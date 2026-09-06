from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.enums import Action, ChainGrade, Decision, Result


def _now() -> datetime:
    return datetime.now(UTC)


def _chain_id() -> str:
    return "chn_" + uuid.uuid4().hex[:20]


class EvidenceTiming(BaseModel):
    """When the operator says the change happened, and how sure that is.

    A versioned, additive extension rather than new columns on the link. Three
    reasons, in order of how much they would have cost to get wrong:

    1. The signed bytes are ``Verdict.model_dump_json()``, stored verbatim and
       served back for verification (``app/db/store.py``). An optional nested
       field leaves every historical ``verdict_json`` byte-identical, so old
       receipts still verify, while new ones commit to this metadata inside the
       same signature — no change to signing behaviour at all.
    2. A reader that ignores ``timing`` reads exactly the link it read before.
       The boolean's meaning is untouched by the date's presence or absence.
    3. ``schema`` says which shape this is, so a future field is an additive
       version bump rather than an ambiguous key.

    What this is NOT: a replacement for the boolean, an input to the score, or
    proof that a swap happened when it says it did. See ``ambiguity_key``.
    """

    schema_version: Literal["swap_timing/1"] = "swap_timing/1"

    # What the operator reported, verbatim and timezone-aware. None whenever
    # `availability` is anything but "available" — including when the operator
    # answered with an explicit null, which means "no date returned" and never
    # "no change ever happened".
    provider_time: datetime | None = None

    # When we asked. Every age below is measured from this instant, not from
    # signing time and not from now, so replaying a receipt a month later
    # reproduces the same number the decision was made on.
    retrieved_at: datetime

    # Age at the moment of the observation, in seconds. None when there is no
    # provider time to measure from.
    age_seconds_at_decision: float | None = None

    # Which external operation produced this, e.g. "sim_swap.retrieve_date".
    # A date is a second priced call, not a field of the boolean's response.
    source_operation: str = ""

    availability: Literal[
        "available",  # a usable timezone-aware timestamp came back
        "unsupported",  # this provider has no date operation for this action
        "no_date",  # the operator answered, explicitly, with no date
        "denied",  # rejected: entitlement, consent or a 4xx
        "timeout",  # no answer arrived in time
        "invalid",  # something came back that cannot be a real event time
        "not_attempted",  # budget did not cover the extra call
    ]

    # A short normalized reason, never provider prose and never an error body.
    reason: str = ""

    # Why this timestamp may not mean what a reader assumes. A key, not a
    # sentence, so it can be rendered in either language: the operator's
    # "latest change" can be an activation or a first association rather than a
    # replacement event.
    ambiguity_key: str = ""

    # How far back the operator actually looked, in days, when it says so.
    # None means the horizon is unknown — which is different from "unlimited",
    # and is why a null date can never be displayed as "never changed".
    monitored_period_days: int | None = None

    # True when the boolean says "changed inside the window" and this date sits
    # outside that same window. Observed on Nokia's hosted simulator on
    # 2026-09-06: +9999…1000 answered `swapped: true` for a 24-hour window and
    # returned 2026-08-18 for the date. The boolean is scenario-driven and is
    # not computed from the date, so the two are separate observations. Kept as
    # a field rather than resolved in code: the honest thing to show a human is
    # that the operator's own two answers disagree.
    disagrees_with_window: bool | None = None


class EvidenceLink(BaseModel):
    """One attested link in the chain — the normalized result of one CAMARA call.

    Note: we deliberately store the *verdict-relevant* fact only (PASS/FLAG + a
    human sentence), never the raw signal (no coordinate or raw phone metadata).
    """

    step: int
    action: Action
    api: str  # human-readable CAMARA API label
    result: Result
    signal: str  # normalized signal name, e.g. "SIM_SWAPPED"
    # Plain-language, e.g. "SIM swap inside the last 240 h". Never free prose:
    # every sentence comes from app/providers/vocabulary.py, so a link can only
    # say what a CAMARA API can actually return.
    detail: str
    consent_basis: str = "n/a"
    source: str = "unknown"  # mock, nac, or another normalized provider
    requires_consent: bool = False
    latency_ms: int = 0
    # The window the question covered, in hours. NOT the age of the event.
    #
    # This distinction is the whole point of the field. CAMARA's SIM Swap and
    # Device Swap `check` operations take a `max_age` and return a BOOLEAN —
    # verified against the recorded responses in docs/nac/, which carry no
    # timestamp of any kind. So "the swap was four hours ago" is not something
    # this boolean can ever state; "no swap in the last 240 hours" is.
    #
    # A date is obtainable, but only from a SEPARATE priced operation
    # (`retrieve-date`), and it lands in `timing` rather than here. The two can
    # disagree — observed on the hosted simulator on 2026-09-06 — so neither is
    # derived from the other. Publishing the window keeps the difference
    # between a fresh check and a ten-day-old one visible without inventing a
    # precision the boolean never gave us.
    #
    # None means the action takes no window (reachability, roaming), or the
    # provider did not record one.
    max_age_hours: float | None = None
    # Optional temporal metadata from a SEPARATE, separately priced provider
    # operation. None means it was never attempted or this provider has none.
    # It never changes `result`, `signal` or `delta_logodds`: the score comes
    # from the boolean, and a date that arrived late or not at all must not
    # move a decision the boolean already made.
    timing: EvidenceTiming | None = None
    delta_logodds: float = 0.0  # how much this link moved the belief
    at: datetime = Field(default_factory=_now)


class Verdict(BaseModel):
    decision: Decision
    # What the chain itself was worth. Part of the signed payload, so the grade
    # is as tamper-evident as the decision it sits beside.
    #
    # None means UNGRADED: a chain issued before grading existed. Every verdict
    # this engine issues now sets it. The default must NOT be a real grade —
    # a chain signed before the field existed would then be served a grade the
    # vault never attested, beside a signature that still reports valid.
    chain_grade: ChainGrade | None = None
    # Keep the legacy signed field name for receipt/API compatibility. Values
    # are policy-derived scores, not empirically calibrated probabilities.
    confidence: float = Field(description=(
        "Policy-derived risk score from 0 to 1; higher is riskier. "
        "Uncalibrated, not a measured fraud probability. Legacy field name."
    ))
    # Where the belief started, in log-odds. Published so a receipt can be
    # recomputed rather than believed: prior + every link's delta = the final
    # log-odds, and 1/(1+e^-total) = confidence. Without it the deltas are
    # unfalsifiable — you can see the steps but not the starting point.
    #
    # 0.0 means NOT RECORDED, not "a prior of zero". A chain signed before this
    # field existed must not be served a prior the vault never attested — the
    # same reasoning as chain_grade above.
    prior_logodds: float = 0.0
    hypothesis: str
    reason: str
    chain_id: str
    chain: list[EvidenceLink] = Field(default_factory=list)
    evidence_cost: float = 0.0
    latency_ms: int = 0
    provider_sources: list[str] = Field(default_factory=list)
    # Which planner produced this run: "llm", "greedy", or "llm+greedy" when it
    # fell back partway. Inside the signed payload, so a chain cannot later be
    # claimed to have been reasoned by a model that did not run it (T3).
    planner: str = "greedy"
    # The thresholds that turned this signed belief into a decision. They must
    # travel with the verdict: using today's policy on yesterday's chain lets a
    # receipt silently rewrite what the signer actually decided.
    policy_snapshot: dict[str, float] = Field(default_factory=dict)

    # --- what this signature is evidence *of* (S5) ---
    # All four are inside the signed bytes. Without them the signature proved
    # only that this server once issued this verdict about something, and a
    # clean chain obtained for any other number verified in a dispute.
    #
    # Defaulted so a row written before S5 still parses on read rather than
    # raising out of Verdict.model_validate_json. An empty subject_hash never
    # matches a subject — see subject.matches — so an old chain reads back as
    # unbound rather than as bound to whatever was asked about.
    subject_hash: str = ""  # HMAC of the E.164 number under a server pepper
    owner_hash: str = ""  # HMAC of the merchant key hash under the same
    request_hash: str = ""  # keyed commitment to the request body
    signed_at: str = ""  # moved inside the signature; see below


class Chain(BaseModel):
    id: str = Field(default_factory=_chain_id)
    hypothesis: str = ""
    links: list[EvidenceLink] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    signed: str | None = None  # Ed25519 signature (evidence vault — Tier 2 stub)

    def add(self, link: EvidenceLink) -> None:
        self.links.append(link)

    def next_step(self) -> int:
        return len(self.links) + 1
