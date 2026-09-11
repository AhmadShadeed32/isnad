from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

import yaml

from app.config import settings
from app.registry import signing

# libyaml when the wheel has it, which is roughly 20x faster to parse and is the
# difference between a startup cost and a noticeable one once the registry holds
# thousands of institutions. Falls back to the pure-Python loader, which is only
# slower, never different — both are the safe loader, so neither constructs
# arbitrary Python objects from the file.
_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# How a number was found, in the order the lookup tries them. EXACT beats
# PREFIX: a switchboard listed explicitly is a stronger statement than the DID
# block it sits inside, and an institution may publish one number from a range
# it otherwise does not call from.
MATCH_EXACT = "exact"
MATCH_PREFIX = "prefix"


@dataclass(frozen=True)
class NumberEntry:
    """One published number, or one block of them, and what it is for."""

    institution_id: str
    institution_name: str
    country: str
    kind: str  # landline | mobile | hotline | pbx_range | shortcode
    outbound: bool  # does the institution actually place calls from it
    basis: str  # published_by_institution | published_by_regulator | demo_fixture
    source: str
    value: str  # the number or prefix exactly as published
    matched_on: str = ""  # MATCH_EXACT | MATCH_PREFIX; empty when not from a lookup


@dataclass
class _Institution:
    id: str
    name: str
    country: str
    basis: str
    source: str
    aliases: list[str] = field(default_factory=list)


class Directory:
    """Which published numbers belong to which institution.

    Three indexes, because the question is asked three ways and only one of them
    is a plain key lookup:

      * exact E.164 -> entry, a dict, O(1);
      * longest matching prefix -> entry, a digit trie, O(len(number)) and so
        bounded at 15 steps by E.164 regardless of how large the registry grows;
      * institution name -> ids, an inverted token index, for "what is this
        bank's real number" — the call-back question.

    Built once at load; nothing here re-reads or re-parses the file. A hit
    allocates one small frozen record to carry how it matched, and that is the
    only allocation on the path. This sits in front of every inbound-call check,
    where a decision that arrives after the phone stops ringing is not a
    decision — measured at ~1µs a lookup, flat from 10 to 10,000 institutions.
    """

    def __init__(self, path: Path, verify_signature: bool = True):
        if verify_signature:
            reason = signing.verify(path, required=settings.registry_signature_required)
            self.signature_state = reason or "signed"
        else:
            self.signature_state = "unchecked"
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_LOADER) or {}
        self._exact: dict[str, NumberEntry] = {}
        self._trie: dict = {}
        self._names: dict[str, set[str]] = {}
        self._institutions: dict[str, _Institution] = {}
        self._name_variants: dict[str, list[set[str]]] = {}
        self._numbers_by_institution: dict[str, list[NumberEntry]] = {}

        # (value, is_prefix, institution_id) for every number declared, in file
        # order. Conflicts are checked once, after the whole file is loaded:
        # an exact number may be declared before the block that swallows it, so
        # an incremental check would depend on the order the file happens to be
        # written in.
        declared: list[tuple[str, bool, str]] = []
        for item in raw.get("institutions") or []:
            self._load_institution(item, path, declared)
        self._reject_conflicts(declared, path)

    # ---- loading ----
    def _load_institution(
        self, item: dict, path: Path, declared: list[tuple[str, bool, str]]
    ) -> None:
        try:
            inst = _Institution(
                id=item["id"],
                name=item["name"],
                country=item.get("country", ""),
                basis=item["basis"],
                source=item["source"],
                aliases=list(item.get("aliases") or []),
            )
        except KeyError as missing:
            # Fail at load, not at lookup. An entry without provenance is an
            # unsourced claim that a phone number belongs to a named bank, and
            # the one thing this file must not do is let one of those through
            # quietly — that is how a scammer's number gets trusted.
            raise ValueError(
                f"{path}: institution {item.get('id', '?')} is missing {missing}"
            ) from None

        if inst.id in self._institutions:
            # A repeated id does not merge, it corrupts: `_institutions` and
            # `_numbers_by_institution` take the second block, `_names`
            # accumulates tokens from both, and `_exact`/`_trie` keep entries
            # stamped with the first block's name. Three indexes, three
            # different answers to "who owns this number".
            raise ValueError(f"{path}: institution id {inst.id!r} is declared twice")

        self._institutions[inst.id] = inst
        self._numbers_by_institution[inst.id] = []

        for token in self._tokens(inst.name, *inst.aliases):
            self._names.setdefault(token, set()).add(inst.id)
        self._name_variants[inst.id] = [
            tokens
            for tokens in (self._tokens(name) for name in (inst.name, *inst.aliases))
            if tokens
        ]

        for number in item.get("numbers") or []:
            value = number.get("number") or number.get("prefix")
            if not value:
                raise ValueError(f"{path}: {inst.id} has an entry with neither number nor prefix")
            entry = NumberEntry(
                institution_id=inst.id,
                institution_name=inst.name,
                country=inst.country,
                kind=number.get("kind", "unknown"),
                # Absent means unknown, and unknown must not read as "yes, they
                # call from here" — that is the assumption an attacker wants.
                outbound=bool(number.get("outbound", False)),
                basis=inst.basis,
                source=inst.source,
                value=value,
            )
            self._numbers_by_institution[inst.id].append(entry)
            is_prefix = "number" not in number
            declared.append((value, is_prefix, inst.id))
            if is_prefix:
                self._insert_prefix(value, entry)
            else:
                self._exact[value] = entry

    def _reject_conflicts(self, declared: list[tuple[str, bool, str]], path: Path) -> None:
        """Refuse to load a file where two institutions can claim one number.

        An entry here asserts that a phone number belongs to a named bank. Two
        institutions asserting it about the same number is not a merge conflict
        to resolve at lookup time by whichever index answers first — it is a
        file that has to be fixed before it is trusted, and the loader's whole
        stated philosophy is to fail at load rather than at lookup.

        Three shapes, all silent before:

          * the same number declared twice — the second overwrote the first;
          * a number carved out of another institution's published block —
            EXACT beats PREFIX, so it silently took the block's numbers;
          * a block inside another institution's block — longest prefix wins,
            so the inner one silently took the range.

        The same number and its own institution's block is NOT a conflict, and
        must not be: publishing a switchboard explicitly inside the DID range
        it sits in is exactly what the registry expects (see MATCH_EXACT).
        """
        seen: dict[str, str] = {}
        for value, _is_prefix, institution_id in declared:
            first = seen.get(value)
            if first is not None:
                raise ValueError(
                    f"{path}: {value} is declared by both {first!r} and "
                    f"{institution_id!r} — one number, one owner"
                )
            seen[value] = institution_id

        # Walk each declared value through the prefix trie and look at every
        # block it falls inside. O(len(value)) per entry rather than a pass over
        # every other entry, so the check stays cheap as the file grows.
        for value, _is_prefix, institution_id in declared:
            for block, owner in self._blocks_containing(value):
                if owner != institution_id:
                    raise ValueError(
                        f"{path}: {value} belongs to {institution_id!r}, but it "
                        f"falls inside {block}, published by {owner!r}"
                    )

    def _blocks_containing(self, value: str) -> list[tuple[str, str]]:
        """Every published block this value sits strictly inside."""
        node = self._trie
        out: list[tuple[str, str]] = []
        for ch in value:
            node = node.get(ch)
            if node is None:
                break
            found = node.get("\x00")
            if found is not None and found[0] != value:
                out.append((found[0], found[1].institution_id))
        return out

    def _insert_prefix(self, prefix: str, entry: NumberEntry) -> None:
        node = self._trie
        for ch in prefix:
            node = node.setdefault(ch, {})
        # A sentinel key that cannot collide with a digit or the leading '+'.
        node["\x00"] = (prefix, entry)

    @staticmethod
    def _tokens(*values: str) -> set[str]:
        """Normalized words for the name index.

        Case- and accent-folded so "Arab Bank", "arab bank" and a copy-paste
        carrying a combining accent all reach the same institution.
        """
        out: set[str] = set()
        for value in values:
            folded = unicodedata.normalize("NFKD", value).casefold()
            for word in "".join(c if c.isalnum() else " " for c in folded).split():
                out.add(word)
        return out

    # ---- lookup ----
    def lookup(self, number: str) -> NumberEntry | None:
        """The institution that published this number, or None.

        None means "not in the registry", which is NOT the same as "not a bank".
        The registry is a small set of institutions someone has sourced; most of
        the phone numbers in the world are absent from it and innocent.
        """
        hit = self._exact.get(number)
        if hit is not None:
            return _matched(hit, MATCH_EXACT)

        node = self._trie
        best: tuple[str, NumberEntry] | None = None
        for ch in number:
            node = node.get(ch)
            if node is None:
                break
            found = node.get("\x00")
            if found is not None:
                best = found  # keep walking: longest prefix wins
        if best is None:
            return None
        return _matched(best[1], MATCH_PREFIX)

    def find_institution(self, name: str) -> list[str]:
        """Institution ids whose name or aliases contain every word given.

        Intersection, not union: "arab bank" should not return every institution
        with "bank" in the name. Ranking is deliberately absent — a directory
        that answers "which number do I call back" must not guess between two
        banks, it must show both.
        """
        tokens = self._tokens(name)
        if not tokens:
            return []
        ids: set[str] | None = None
        for token in tokens:
            matches = self._names.get(token, set())
            ids = matches.copy() if ids is None else (ids & matches)
            if not ids:
                return []
        return sorted(ids or set())

    def numbers_for(self, institution_id: str) -> list[NumberEntry]:
        return list(self._numbers_by_institution.get(institution_id, []))

    def check_claim(self, claimed: str | None, entry: NumberEntry) -> bool | None:
        """Does free-text `claimed` name the institution this number belongs to?

        Three answers, and the third is the important one:

          * ``True``  — the claim contains every word of the institution's name
            (or of one of its aliases). "Demo Bank", "Demo Bank customer
            service" and "Demo Bank, Fraud Dept." all say the same thing.
          * ``False`` — the claim does not name this institution and does
            positively name a **different** one that is in the registry. That is
            the only shape of claim this file can honestly call a mismatch.
          * ``None``  — no assertion. An unindexed name, a bare "bank", an
            empty string: the registry has nothing to say, and saying
            ``REGISTRY_CLAIM_MISMATCH`` here would condemn honest callers for
            describing themselves in words this file has never seen.

        Subset, not equality, and in that direction: the institution's tokens
        must be inside the claim. Equality would fail every honest caller who
        adds a department to their name; the reverse direction (claim inside
        the institution) is `find_institution`'s question, and it would let a
        bare "bank" match Demo Bank.

        `claimed` is caller-controlled text (S11). It is compared here and never
        rendered, never interpolated, and never put in a prompt — the caller
        learns only how it compared, which is something they already know.
        """
        tokens = self._tokens(claimed or "")
        if not tokens:
            return None
        if self._is_named_by(tokens, entry.institution_id):
            return True
        # Owner first, deliberately: a claim naming both the owner and someone
        # else has still named the owner, and is not a mismatch.
        candidates: set[str] = set()
        for token in tokens:
            candidates |= self._names.get(token, set())
        candidates.discard(entry.institution_id)
        for institution_id in sorted(candidates):
            if self._is_named_by(tokens, institution_id):
                return False
        return None

    def _is_named_by(self, tokens: set[str], institution_id: str) -> bool:
        """Do the claim's words contain a whole name — or a whole alias?

        Per variant, never the union of them: "Demo Bank" is the institution's
        name, and testing it against {demo, bank, jordan, fraud, department}
        (name and aliases merged) would reject the institution's own name.
        """
        return any(variant <= tokens for variant in self._name_variants.get(institution_id, ()))

    @property
    def size(self) -> tuple[int, int]:
        """(institutions, indexed numbers) — for the health//registry endpoints."""
        return len(self._institutions), len(self._exact) + self._count_prefixes(self._trie)

    def _count_prefixes(self, node: dict) -> int:
        total = 1 if "\x00" in node else 0
        for key, child in node.items():
            if key != "\x00":
                total += self._count_prefixes(child)
        return total


def _matched(entry: NumberEntry, how: str) -> NumberEntry:
    """The same entry, stamped with how the lookup reached it."""
    return replace(entry, matched_on=how)


@lru_cache(maxsize=8)
def get_directory(registry_path: str) -> Directory:
    """Load and index the registry once and reuse it — same contract as
    `get_engine`: parsing YAML per inbound call would be the slowest thing in a
    path whose whole point is that it beats the second ring."""
    return Directory(Path(registry_path))
