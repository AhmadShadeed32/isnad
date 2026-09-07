"""The number registry — which published numbers belong to which institution.

The network layer attests the LINE a call comes from. It has no idea what an
institution is called, so it cannot answer "is +962 6 500 0000 Arab Bank?".
This does. The pair is the point, and the tests that matter most here are the
ones asserting what a registry hit does NOT mean.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.registry import signing
from app.registry.directory import Directory, get_directory

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


def _directory() -> Directory:
    return get_directory(str(settings.registry_path))


def _written(institutions: list[dict]) -> Directory:
    path = Path(tempfile.mkstemp(suffix=".yaml")[1])
    path.write_text(yaml.safe_dump({"institutions": institutions}), encoding="utf-8")
    try:
        return Directory(path)
    finally:
        path.unlink()


_SOURCED = {
    "id": "acme",
    "name": "Acme Bank",
    "country": "JO",
    "basis": "demo_fixture",
    "source": "test fixture",
    "verified_on": "2026-08-30",
}


# ---- lookup ----


def test_an_exact_number_resolves_to_its_institution():
    entry = _directory().lookup("+96265000000")
    assert entry is not None
    assert entry.institution_name == "Demo Bank"
    assert entry.matched_on == "exact"


def test_an_extension_resolves_through_the_published_block():
    """Institutions own ranges, not single numbers.

    A registry of exact numbers alone would miss every extension behind the
    switchboard, which is most of the numbers a customer is ever called from.
    """
    entry = _directory().lookup("+962650001234")
    assert entry is not None
    assert entry.matched_on == "prefix"
    assert entry.value == "+9626500"


def test_the_longest_prefix_wins():
    """An institution may publish a block inside a block — a branch range
    carved out of the corporate one — and the more specific statement is the
    one that answers. Both must belong to the same institution: two
    institutions nesting blocks is a conflict the loader now refuses (see
    below), because a number cannot have two owners.
    """
    directory = _written(
        [
            {
                **_SOURCED,
                "numbers": [
                    {"prefix": "+9626", "kind": "pbx_range"},
                    {"prefix": "+96265000", "kind": "landline"},
                ],
            },
        ]
    )
    assert directory.lookup("+962650001234").kind == "landline"
    assert directory.lookup("+962699999999").kind == "pbx_range"


def test_an_exact_entry_beats_the_block_it_sits_inside():
    """An institution may list one number out of a range it otherwise does not
    call from, and the specific statement is the stronger one."""
    directory = _written(
        [
            {
                **_SOURCED,
                "numbers": [
                    {"prefix": "+9626500", "kind": "pbx_range", "outbound": True},
                    {"number": "+96265000999", "kind": "hotline", "outbound": False},
                ],
            },
        ]
    )
    assert directory.lookup("+96265000999").kind == "hotline"
    assert directory.lookup("+96265000998").kind == "pbx_range"


def test_an_unlisted_number_is_unknown_not_suspicious():
    """Absence from the registry is not evidence of anything. Most numbers in
    the world are not in this file and are perfectly ordinary."""
    assert _directory().lookup("+96279999999") is None


# ---- what a hit does NOT mean ----


def test_a_published_inbound_only_line_is_flagged_as_never_outbound():
    """A hotline printed on the back of a card is a convenient thing to spoof,
    precisely because customers recognise it. If it appears as caller ID it was
    not dialled from — the institution never places calls on it."""
    entry = _directory().lookup("+96280022222")
    assert entry is not None and entry.outbound is False


def test_outbound_defaults_to_false_when_unstated():
    """Unknown must not read as "yes, they call from here" — that is precisely
    the assumption an attacker benefits from."""
    directory = _written([{**_SOURCED, "numbers": [{"number": "+96260000000"}]}])
    assert directory.lookup("+96260000000").outbound is False


def test_a_registry_hit_carries_its_basis_and_source():
    """Same rule as the pricing block in policy.yaml: an entry here asserts that
    a phone number belongs to a named bank, and an unsourced assertion of that
    kind is a way to get a scammer's number trusted."""
    entry = _directory().lookup("+96265000000")
    assert entry.basis and entry.source


def test_an_entry_without_provenance_fails_at_load_not_at_lookup():
    with pytest.raises(ValueError, match="missing"):
        _written([{"id": "x", "name": "No Source", "numbers": []}])


def test_an_entry_with_neither_number_nor_prefix_fails_at_load():
    with pytest.raises(ValueError, match="neither number nor prefix"):
        _written([{**_SOURCED, "numbers": [{"kind": "landline"}]}])


# ---- name search: the call-back question ----


def test_institution_search_requires_every_word():
    """Intersection, not union: "arab bank" must not return every institution
    with "bank" in the name."""
    directory = _written(
        [
            {**_SOURCED, "numbers": [{"number": "+96260000001"}]},
            {
                **_SOURCED,
                "id": "beta",
                "name": "Beta Bank",
                "numbers": [{"number": "+96260000002"}],
            },
        ]
    )
    assert directory.find_institution("acme bank") == ["acme"]
    assert sorted(directory.find_institution("bank")) == ["acme", "beta"]
    assert directory.find_institution("acme beta") == []


def test_institution_search_is_case_and_accent_folded():
    """The name reaches this from a copy-paste, a phone keyboard, or another
    system's export, and any of those can carry a combining accent or a
    full-width character the original did not have."""
    assert _directory().find_institution("DEMO BANK") == ["demo-bank-jo"]
    assert _directory().find_institution("demo  bank") == ["demo-bank-jo"]

    # An actual accent — the old test's name promised one and none appeared.
    directory = _written(
        [
            {
                **_SOURCED,
                "id": "cafe",
                "name": "Café Bank",
                "numbers": [{"number": "+96260000003"}],
            },
        ]
    )
    assert directory.find_institution("Café Bank") == ["cafe"]
    # Decomposed: "e" + U+0301 COMBINING ACUTE, which is what a paste from many
    # systems actually contains and is a different byte string entirely.
    assert directory.find_institution("Cafe\u0301 Bank") == ["cafe"]
    # Full-width, from an East Asian keyboard or a CJK-locale export.
    assert directory.find_institution("\uff23\uff41\uff46\uff45\u0301 Bank") == ["cafe"]


def test_an_alias_finds_the_institution():
    assert _directory().find_institution("Demo Bank fraud department") == ["demo-bank-jo"]


# ---- conflicts: a number cannot have two owners ----


def test_two_institutions_cannot_publish_the_same_number():
    """Silently, the second one won — the later write to `_exact` replaced the
    earlier. A file that says a number belongs to two banks has to be fixed,
    not resolved at lookup time by whichever entry was parsed last."""
    with pytest.raises(ValueError, match="one number, one owner"):
        _written(
            [
                {**_SOURCED, "numbers": [{"number": "+96260000001"}]},
                {
                    **_SOURCED,
                    "id": "beta",
                    "name": "Beta Bank",
                    "numbers": [{"number": "+96260000001"}],
                },
            ]
        )


def test_a_number_cannot_be_carved_out_of_another_institutions_block():
    """EXACT beats PREFIX, so this silently took one number out of a range
    somebody else published — the cheapest way to get a single number attributed
    to the wrong bank."""
    with pytest.raises(ValueError, match="falls inside"):
        _written(
            [
                {**_SOURCED, "numbers": [{"prefix": "+9626500", "kind": "pbx_range"}]},
                {
                    **_SOURCED,
                    "id": "beta",
                    "name": "Beta Bank",
                    "numbers": [{"number": "+96265001234"}],
                },
            ]
        )


def test_a_block_cannot_be_carved_out_of_another_institutions_block():
    """Longest prefix wins, so the inner block silently took the range —
    whichever order the two are written in."""
    for institutions in (
        [
            {**_SOURCED, "numbers": [{"prefix": "+9626", "kind": "pbx_range"}]},
            {
                **_SOURCED,
                "id": "beta",
                "name": "Beta Bank",
                "numbers": [{"prefix": "+96265000", "kind": "pbx_range"}],
            },
        ],
        [
            {
                **_SOURCED,
                "id": "beta",
                "name": "Beta Bank",
                "numbers": [{"prefix": "+96265000", "kind": "pbx_range"}],
            },
            {**_SOURCED, "numbers": [{"prefix": "+9626", "kind": "pbx_range"}]},
        ],
    ):
        with pytest.raises(ValueError, match="falls inside"):
            _written(institutions)


def test_an_institution_may_publish_a_number_inside_its_own_block():
    """The case that must NOT be rejected: a switchboard listed explicitly
    inside the DID range it sits in is exactly what the registry expects, and
    the shipped file does it."""
    directory = _written(
        [
            {
                **_SOURCED,
                "numbers": [
                    {"prefix": "+9626500", "kind": "pbx_range", "outbound": True},
                    {"number": "+96265000000", "kind": "landline", "outbound": True},
                ],
            },
        ]
    )
    assert directory.lookup("+96265000000").matched_on == "exact"


def test_a_duplicate_institution_id_is_refused():
    """It did not merge, it corrupted: the second block took `_institutions` and
    `_numbers_by_institution`, `_names` accumulated tokens from both, and
    `_exact` kept entries stamped with the FIRST block's name. Three indexes,
    three different answers."""
    with pytest.raises(ValueError, match="declared twice"):
        _written(
            [
                {**_SOURCED, "numbers": [{"number": "+96260000001"}]},
                {**_SOURCED, "name": "Acme Bank Again", "numbers": [{"number": "+96260000002"}]},
            ]
        )


def test_the_shipped_registry_has_no_conflicts():
    """The check is only worth having if it runs against the file that ships."""
    assert _directory().size[0] >= 1


# ---- the claim comparison: match, mismatch, and "cannot say" ----


def _two_banks() -> Directory:
    return _written(
        [
            {
                **_SOURCED,
                "aliases": ["Acme Bank Jordan"],
                "numbers": [{"number": "+96260000001", "outbound": True}],
            },
            {
                **_SOURCED,
                "id": "beta",
                "name": "Beta Bank",
                "numbers": [{"number": "+96260000002", "outbound": True}],
            },
        ]
    )


def test_a_caller_who_describes_themselves_more_fully_still_matches():
    """The bug this replaced: every word of the claim had to be indexed, so the
    more completely an honest caller named themselves the more likely they were
    condemned — and REGISTRY_CLAIM_MISMATCH goes into the SIGNED chain."""
    directory = _two_banks()
    entry = directory.lookup("+96260000001")
    assert entry is not None
    for claim in (
        "Acme Bank",
        "Acme Bank customer service",
        "Acme Bank Ltd",
        "Acme Bank, Fraud Dept.",
        "acme bank",
    ):
        assert directory.check_claim(claim, entry) is True, claim


def test_an_alias_is_matched_whole_and_not_merged_with_the_name():
    """Name and aliases share one token index, so a merged subset test would
    reject the institution's own name for lacking a word from an alias."""
    directory = _two_banks()
    entry = directory.lookup("+96260000001")
    assert directory.check_claim("Acme Bank Jordan fraud team", entry) is True


def test_a_bare_generic_word_is_not_a_match():
    """The converse hole in the old comparison: "bank" alone matched every bank,
    because the test ran claim-inside-institution instead of the other way."""
    directory = _two_banks()
    entry = directory.lookup("+96260000001")
    assert directory.check_claim("bank", entry) is None
    assert directory.check_claim("the bank", entry) is None


def test_a_mismatch_needs_the_claim_to_name_a_DIFFERENT_indexed_institution():
    directory = _two_banks()
    entry = directory.lookup("+96260000001")
    assert directory.check_claim("Beta Bank", entry) is False
    assert directory.check_claim("Beta Bank collections", entry) is False


def test_an_unknown_name_is_no_verdict_rather_than_a_mismatch():
    directory = _two_banks()
    entry = directory.lookup("+96260000001")
    assert directory.check_claim("Arab Bank", entry) is None
    assert directory.check_claim("", entry) is None
    assert directory.check_claim(None, entry) is None
    assert directory.check_claim("!!! ???", entry) is None


def test_naming_the_owner_wins_over_also_naming_someone_else():
    """A claim that contains the owner's name has named the owner. Order the
    checks the other way and "Acme Bank, formerly Beta Bank" is a mismatch."""
    directory = _two_banks()
    entry = directory.lookup("+96260000001")
    assert directory.check_claim("Acme Bank, formerly Beta Bank", entry) is True


# ---- the API ----


def test_lookup_endpoint_returns_the_match_and_how_it_was_made():
    body = client.get("/v1/registry/lookup", params={"number": "+96265000000"}, headers=AUTH).json()
    assert body["found"] is True
    assert body["match"]["institution_name"] == "Demo Bank"
    assert body["match"]["matched_on"] == "exact"
    assert body["match"]["source"]


def test_lookup_endpoint_says_how_much_it_searched_before_missing():
    """ "Not found" is only readable next to the size of the thing that failed
    to find it."""
    body = client.get("/v1/registry/lookup", params={"number": "+96279999999"}, headers=AUTH).json()
    assert body["found"] is False and body["match"] is None
    assert body["institutions_indexed"] >= 1 and body["registry_size"] >= 1


def test_the_claim_is_compared_against_the_registry():
    match = client.get(
        "/v1/registry/lookup",
        params={"number": "+96265000000", "claimed_identity": "Demo Bank"},
        headers=AUTH,
    ).json()["match"]
    assert match["claim_matches_registry"] is True

    # A name the registry has never heard of is not a mismatch. It cannot be:
    # the registry holds a handful of institutions and knows nothing about the
    # rest of the world's, so "not one of mine" is ignorance, not evidence.
    unknown = client.get(
        "/v1/registry/lookup",
        params={"number": "+96265000000", "claimed_identity": "Arab Bank"},
        headers=AUTH,
    ).json()["match"]
    assert unknown["claim_matches_registry"] is None


def test_no_claim_means_no_verdict_about_the_claim():
    match = client.get(
        "/v1/registry/lookup", params={"number": "+96265000000"}, headers=AUTH
    ).json()["match"]
    assert match["claim_matches_registry"] is None


def test_the_caller_supplied_claim_is_never_echoed_back():
    """S11 — caller-controlled text is compared, never rendered. The response
    says whether it matched and nothing else, so the registry cannot be used to
    reflect an attacker's string into whatever renders this."""
    marker = "<img src=x onerror=alert(1)>"
    body = client.get(
        "/v1/registry/lookup",
        params={"number": "+96265000000", "claimed_identity": marker},
        headers=AUTH,
    )
    assert marker not in body.text
    assert body.json()["match"]["claim_matches_registry"] is None


def test_institution_endpoint_answers_the_call_back_question():
    body = client.get("/v1/registry/institution", params={"name": "demo bank"}, headers=AUTH).json()
    assert len(body) == 1
    numbers = {n["value"]: n for n in body[0]["numbers"]}
    assert "+96265000000" in numbers
    # The hotline is returned with its direction, so a UI can say "call this,
    # they never call you from it" rather than presenting them as equivalent.
    assert numbers["+96280022222"]["outbound"] is False


def test_the_registry_requires_a_key():
    assert client.get("/v1/registry/lookup", params={"number": "+96265000000"}).status_code in (
        401,
        403,
    )


def test_a_malformed_number_is_rejected_before_lookup():
    assert (
        client.get("/v1/registry/lookup", params={"number": "nope"}, headers=AUTH).status_code
        == 422
    )


# ---- the shipped file ----


def test_nothing_in_the_shipped_registry_claims_to_be_real():
    """Guards the one mistake that would matter: a demo fixture shipping as a
    published fact about a real bank. Every entry is currently invented, and
    must say so until someone sources a real one.
    """
    raw = yaml.safe_load(Path(settings.registry_path).read_text(encoding="utf-8"))
    for institution in raw["institutions"]:
        assert institution["basis"] in {
            "demo_fixture",
            "published_by_institution",
            "published_by_regulator",
        }
        assert institution["source"], f"{institution['id']} has no source"


# ---- signing (item 4 of the 31 Aug plan) ----


def test_the_shipped_registry_is_signed_and_valid():
    """An entry here asserts a phone number belongs to a named bank. Re-run
    scripts/sign_registry.py after every edit or this fails."""
    assert signing.verify(Path(settings.registry_path)) is None


def test_a_tampered_registry_refuses_to_load():
    """The demo: change one digit, watch it refuse. A registry that loads after
    being edited is a registry that can be edited."""
    directory_path = Path(tempfile.mkstemp(suffix=".yaml")[1])
    directory_path.write_text(
        yaml.safe_dump({"institutions": [dict(_SOURCED, numbers=[{"number": "+96260000001"}])]}),
        encoding="utf-8",
    )
    signing.write(directory_path)
    assert Directory(directory_path).lookup("+96260000001") is not None

    directory_path.write_text(
        directory_path.read_text(encoding="utf-8").replace("+96260000001", "+96260000002"),
        encoding="utf-8",
    )
    with pytest.raises(signing.RegistryTampered):
        Directory(directory_path)


def test_an_unsigned_registry_loads_but_says_so():
    """A MISSING signature is an unsigned dev file; a WRONG one is tampering.
    They are different facts and must not share a code path."""
    path = Path(tempfile.mkstemp(suffix=".yaml")[1])
    path.write_text(yaml.safe_dump({"institutions": []}), encoding="utf-8")
    directory = Directory(path)
    assert "unsigned" in directory.signature_state


def test_an_unsigned_registry_is_fatal_when_signatures_are_required(monkeypatch):
    monkeypatch.setattr(settings, "registry_signature_required", True, raising=False)
    path = Path(tempfile.mkstemp(suffix=".yaml")[1])
    path.write_text(yaml.safe_dump({"institutions": []}), encoding="utf-8")
    with pytest.raises(signing.RegistryTampered):
        Directory(path)


def test_a_signature_from_an_untrusted_key_is_rejected():
    """Otherwise an attacker who can write both files re-signs with their own
    key and the check passes."""
    path = Path(tempfile.mkstemp(suffix=".yaml")[1])
    path.write_text(yaml.safe_dump({"institutions": []}), encoding="utf-8")
    signing.write(path)

    sig_path = signing.signature_path(path)
    record = json.loads(sig_path.read_text(encoding="utf-8"))
    record["public_key"] = "00" * 32
    sig_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(signing.RegistryTampered, match="does not trust"):
        Directory(path)


def test_an_unreadable_signature_is_tampering_not_absence():
    """ "I could not parse the proof" must never be cheaper than "the proof
    failed"."""
    path = Path(tempfile.mkstemp(suffix=".yaml")[1])
    path.write_text(yaml.safe_dump({"institutions": []}), encoding="utf-8")
    signing.signature_path(path).write_text("not json", encoding="utf-8")
    with pytest.raises(signing.RegistryTampered, match="unreadable"):
        Directory(path)


def test_the_registry_signature_is_domain_separated():
    """The vault key also signs evidence chains. Without a prefix naming which
    kind of document the bytes are, a signature over one could be presented as
    a signature over the other."""
    from app.chain.vault import vault

    body = b"institutions: []\n"
    record = signing.sign_bytes(body)
    assert vault.verify(signing.payload_for(body), record.signature)
    # The same signature must NOT verify over the undecorated bytes.
    assert not vault.verify(body, record.signature)


def test_render_requires_the_bundled_registry_signature(monkeypatch, tmp_path):
    """The blueprint's trust pin verifies the shipped file and fails closed."""
    import shutil

    blueprint = yaml.safe_load(Path("render.yaml").read_text())
    env = {item["key"]: item["value"] for item in blueprint["services"][0]["envVars"]}
    assert env["ISNAD_REGISTRY_SIGNATURE_REQUIRED"] == "true"
    monkeypatch.setattr(settings, "vault_trusted_public_keys",
                        env["ISNAD_VAULT_TRUSTED_PUBLIC_KEYS"])
    registry = tmp_path / "registry.yaml"
    shutil.copyfile("app/registry/registry.yaml", registry)
    signature = signing.signature_path(registry)
    shutil.copyfile("app/registry/registry.yaml.sig", signature)
    assert signing.verify(registry, required=True) is None
    registry.write_text(registry.read_text() + "\n# altered\n")
    with pytest.raises(signing.RegistryTampered, match="does not match"):
        signing.verify(registry, required=True)
    signature.unlink()
    with pytest.raises(signing.RegistryTampered, match="missing"):
        signing.verify(registry, required=True)


def test_startup_survives_a_deployment_that_has_no_signature(monkeypatch, tmp_path):
    """The unsigned path must stay viable, or the fix for the above is a
    different outage."""
    registry = tmp_path / "registry.yaml"
    registry.write_text(yaml.safe_dump({"institutions": []}), encoding="utf-8")
    monkeypatch.setattr(settings, "registry_path", registry, raising=False)
    monkeypatch.setattr(settings, "registry_signature_required", False, raising=False)

    from app.main import _check_registry_signature

    _check_registry_signature()  # warns, does not raise
