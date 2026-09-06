from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.chain.models import EvidenceLink
from app.config import settings
from app.domain.enums import ChainGrade, Decision
from app.presentation import Presentation

# Read once at import: it is a validation constraint, not a runtime lookup.
SESSION_TTL_CEILING_SECONDS = settings.session_max_ttl_seconds


class Money(BaseModel):
    value: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class Area(BaseModel):
    """A claimed location — never a tracked coordinate. Used only for yes/no verify."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_m: int = Field(default=2000, gt=0, le=50000)


class RequestContext(BaseModel):
    event: Literal[
        "signup",
        "checkout",
        "payout",
        "password_reset",
        "profile_change",
        "inbound_call",
        "session_monitor",
    ] = "checkout"
    amount: Money | None = None
    payment_method: str | None = None  # e.g. "cod", "card"
    account_age_days: int | None = Field(default=None, ge=0)
    claimed_location: Area | None = None


class Figure(BaseModel):
    """A number that knows where it came from (T5).

    Provenance travels with the value all the way to the screen, because a
    figure a judge checks and finds invented is worse than no figure.
    """

    value: float | None
    basis: str  # measured | list_price | estimate | unpriced
    source: str


class Alternative(BaseModel):
    """What the same decision would have cost as one SMS OTP (T5)."""

    isnad_calls: Figure
    isnad_latency_ms: Figure
    isnad_cost_usd: Figure
    otp_messages: Figure
    otp_cost_usd: Figure
    otp_seconds: Figure
    otp_dropoff_rate: Figure
    # What the OTP path's drop-off is worth in money, and what one false decline
    # costs. Both null unless the merchant has priced them — an invented figure
    # here would undo the point the whole block exists to make.
    otp_dropoff_cost_usd: Figure
    false_decline_cost_usd: Figure
    country: str
    currency: str
    note: str = (
        "List prices and published estimates, not measurements of this "
        "transaction. Sources are in app/policy/policy.yaml."
    )


class VerifyOptions(BaseModel):
    return_chain: bool = True
    # Fire the top N affordable checks at once instead of one at a time. Buys
    # wall-clock and spends more, so policy.yaml says "opt in per request, never
    # globally" — and until this field existed no route let anyone do that, so
    # the only way in was the policy-wide default the comment warns against.
    # None means "whatever policy says", which is sequential.
    parallel: bool | None = None


class VerificationRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+[1-9]\d{7,14}$", examples=["+962790000001"])
    context: RequestContext = Field(default_factory=RequestContext)
    options: VerifyOptions = Field(default_factory=VerifyOptions)


class VerificationResponse(BaseModel):
    decision: Decision
    # Which planner produced the run: "llm", "greedy", or "llm+greedy" (T3).
    planner: str = "greedy"
    # null = ungraded (issued before chain grading existed), never a real grade.
    chain_grade: ChainGrade | None = None
    confidence: float
    hypothesis: str
    reason: str
    chain_id: str
    chain: list[EvidenceLink] | None = None
    evidence_cost: float = 0.0
    latency_ms: int = 0
    evidence_steps: int = 0
    provider_sources: list[str] = Field(default_factory=list)
    # What one SMS OTP would have cost instead (T5). Every figure carries its
    # basis and source so a caller can label them as honestly as we do.
    alternative: Alternative | None = None
    # Plain-language projection of this same verdict (P2). Optional and always
    # additive: a client or cached response that predates this field simply
    # sees None and falls back to `reason`. Never derived from anything other
    # than the verdict it travels beside -- see app/presentation.py.
    presentation: Presentation | None = None


ConsentStatus = Literal[
    "PENDING",
    "EXCHANGING",
    "AUTHORIZED",
    "VERIFYING",
    "COMPLETED",
    "DENIED",
    "FAILED",
    "EXPIRED",
]


class NumberVerificationConsentResponse(BaseModel):
    consent_id: str
    status: ConsentStatus
    authorization_url: str | None = None
    expires_at: str
    chain_id: str | None = None
    reason: str | None = None


class ExplainRequest(BaseModel):
    """Ask the agent about a decision it already made (T4).

    Capped at 280 characters: it is untrusted text from a member of the public,
    and a question that needs more than a tweet is not a question about one chain.
    """

    question: str = Field(
        ...,
        min_length=3,
        max_length=280,
        examples=["Why did this get challenged rather than declined?"],
    )


class ExplainResponse(BaseModel):
    chain_id: str
    question: str
    answer: str


class SubjectCheckRequest(BaseModel):
    """Ask whether a stored chain was really issued about this number (S5)."""

    phone_number: str = Field(..., pattern=r"^\+[1-9]\d{7,14}$", examples=["+962790000001"])


# --- Reverse Isnad: verify an inbound caller to the customer ---


class ReverseVerificationRequest(BaseModel):
    caller_number: str = Field(..., pattern=r"^\+[1-9]\d{7,14}$", examples=["+96265000000"])
    # The number being called. Needed only to match a Verified Caller
    # announcement, which is bound to BOTH ends: matching the caller alone would
    # let one genuine announcement verify a burst of spoofed calls to everyone
    # else for as long as its window stood. Optional — without it that check
    # cannot run, which is not the same as it failing.
    callee_number: str | None = Field(default=None, pattern=r"^\+[1-9]\d{7,14}$")
    # Free text validated only for length used to be spliced into a prose
    # `reason` returned to a merchant who will very plausibly render it (S11).
    # Constrained to the shape an organisation name actually has: letters
    # (any script, so Arabic names work), digits, spaces and a few separators.
    # No angle brackets, no quotes, no control characters.
    claimed_identity: str = Field(
        ...,
        min_length=2,
        max_length=120,
        # A literal space rather than \s: \s admits newlines and tabs, and a
        # multi-line "organisation name" is a formatting-injection channel into
        # anything that renders it.
        pattern=r"^[\w .,'()&\-]+$",
        examples=["Bank of Jordan"],
    )
    customer_number: str | None = Field(default=None, pattern=r"^\+[1-9]\d{7,14}$")
    options: VerifyOptions = Field(default_factory=VerifyOptions)


class ReverseVerificationResponse(BaseModel):
    trust: str  # TRUST_CALLER | CAUTION | REJECT_CALLER
    chain_grade: ChainGrade | None = None
    confidence: float  # P(impersonation)
    claimed_identity: str
    reason: str
    chain_id: str
    chain: list[EvidenceLink] | None = None


# --- Trust with a TTL: live session revocation ---


class SessionCreateRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+[1-9]\d{7,14}$", examples=["+962790000001"])
    # Bounded by settings.session_max_ttl_seconds rather than the old 86400
    # ceiling: every session polls two billed CAMARA APIs on a timer, so the TTL
    # a caller supplies is a direct multiplier on someone else's bill (S7a).
    # Rejected at the edge as a 422 rather than silently clamped, so a caller
    # asking for a day is told no instead of quietly getting five minutes.
    ttl_seconds: int | None = Field(default=None, ge=0, le=SESSION_TTL_CEILING_SECONDS)


class SessionResponse(BaseModel):
    session_id: str
    status: str  # ACTIVE | REVOKED | ENDED | EXPIRED
    phone_number: str
    reason: str | None = None
    created_at: str
    expires_at: str


# --- Number registry -------------------------------------------------------
# The network attests the line; the registry attests the name on it. Neither is
# sufficient alone, which is why every field below says how it was established.


class RegistryMatch(BaseModel):
    """One institution's claim on a number, with the basis for the claim."""

    institution_id: str
    institution_name: str
    country: str
    kind: str
    # Whether the institution actually places calls from this line. A published
    # inbound-only hotline appearing as caller ID was spoofed by definition.
    outbound: bool
    matched_on: str  # exact | prefix
    matched_value: str  # the number or block that matched
    basis: str
    source: str
    # None when the caller made no claim. Compared, never rendered (S11).
    claim_matches_registry: bool | None = None


class RegistryLookupResponse(BaseModel):
    number: str
    found: bool
    match: RegistryMatch | None = None
    # Absent from the registry is not evidence of anything. These two say how
    # much was searched, so "not found" can be read against the size of the
    # thing that failed to find it.
    registry_size: int
    institutions_indexed: int


class RegistryNumber(BaseModel):
    value: str
    kind: str
    outbound: bool


class RegistryInstitution(BaseModel):
    institution_id: str
    institution_name: str
    country: str
    basis: str
    source: str
    numbers: list[RegistryNumber]


# --- Verified Caller ---------------------------------------------------------
# Field names follow CAMARA VerifiedCaller `verified-caller.yaml` (Sandbox tier,
# v0.1.0, Fall25 meta-release). Implementing the published contract rather than
# inventing one is the difference between being early to a standard and being
# incompatible with it — and there is nothing to be compatible WITH yet: the API
# has zero commercial operator launches and is absent from Nokia NaC, so this
# service answers it locally and says so.


class PreAnnounceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    calling_participant: str = Field(alias="callingParticipant", pattern=r"^\+[1-9]\d{7,14}$")
    called_participant: str = Field(alias="calledParticipant", pattern=r"^\+[1-9]\d{7,14}$")
    strategy: str = Field(default="BRAND_DISPLAY", pattern=r"^(BRAND_DISPLAY|SMS)$")
    time_to_live: int | None = Field(default=None, alias="timeToLive", ge=1, le=300)
    # A literal space rather than \s, for the same reason claimed_identity uses
    # one: \s admits newlines, and a multi-line display name is a formatting
    # injection channel into whatever renders the incoming call.
    dynamic_display_name: str = Field(
        default="",
        alias="dynamicDisplayName",
        max_length=120,
        pattern=r"^[\w .,:'&()\-]*$",
    )
    call_reason: str = Field(
        default="",
        alias="callReason",
        max_length=160,
        pattern=r"^[\w .,:'&()\-/]*$",
    )


class PreAnnounceResponse(BaseModel):
    announcement_id: str
    institution_id: str
    strategy: str
    expires_at: datetime
    # Echoed so an integrator can see the window actually granted, which may be
    # shorter than the one asked for.
    time_to_live_seconds: int


class ScreenRequest(BaseModel):
    """Tier 1 — the pre-ring check. Local state only, no network calls."""

    caller_number: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    callee_number: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    # The same charset the reverse request's claimed_identity carries (S11), and
    # for the same reason: caller-controlled free text validated only for length
    # reaches a comparison here and a signed chain on the Tier 2 path. `*` not
    # `+` because this one is optional.
    claimed_identity: str = Field(
        default="",
        max_length=120,
        pattern=r"^[\w .,'()&\-]*$",
    )


class ScreenResponse(BaseModel):
    # VERIFIED_INSTITUTION — an institution announced this exact call and proved
    #   who it was to do so.
    # SUSPECTED_SPOOF — the number is published as one the institution never
    #   calls from, or the claim does not match the number's owner.
    # UNKNOWN — nothing local can say. The honest majority case, and it must not
    #   be dressed up as either of the others.
    label: str
    reason: str
    caller_number: str
    institution_name: str | None = None
    # What produced the label, so a client never has to infer it.
    basis: str
    # Tier 1 makes no network call by construction. Stated in the response so a
    # caller cannot mistake it for a full chain.
    tier: int = 1
    elapsed_us: int = 0


# --- CHALLENGE followups (P3) ---
#
# What a merchant did after a signed CHALLENGE decision. Deliberately separate
# from VerificationResponse: these requests carry no free text, because a
# merchant-supplied note here would be exactly the kind of unstructured input
# T3 already keeps out of anything the agent or a receipt renders.

ChallengeMethod = Literal["manual_review"]
ChallengeResult = Literal["PASSED", "FAILED", "ABANDONED"]
ChallengeStatus = Literal["PENDING", "PASSED", "FAILED", "ABANDONED", "EXPIRED"]


class ChallengeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: ChallengeMethod = "manual_review"


class ChallengeCreateResponse(BaseModel):
    attempt_id: str
    chain_id: str
    method: ChallengeMethod
    status: ChallengeStatus
    created_at: str
    expires_at: str


class ChallengeEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: ChallengeResult


class ChallengeEventResponse(BaseModel):
    attempt_id: str
    status: ChallengeStatus
    result: ChallengeResult
    reported_at: str


class ChallengeEventSummary(BaseModel):
    result: ChallengeResult
    provenance: str
    reported_at: str


class ChallengeAttemptSummary(BaseModel):
    attempt_id: str
    method: ChallengeMethod
    status: ChallengeStatus
    created_at: str
    expires_at: str
    events: list[ChallengeEventSummary]


class ChallengeTimelineResponse(BaseModel):
    chain_id: str
    attempts: list[ChallengeAttemptSummary]


# --- Merchant outcome reporting (P5) ---
#
# Order status and fraud assessment are independent dimensions, each its own
# append-only correction chain. Challenge execution — the third dimension the
# handoff names — is not reported through here at all: it already exists in
# P3's own tables and is read fresh from there.

OrderStatusValue = Literal["ACCEPTED", "FULFILLED", "CANCELLED", "UNKNOWN"]
FraudAssessmentValue = Literal["CONFIRMED_FRAUD", "CONFIRMED_LEGITIMATE", "INCONCLUSIVE", "UNKNOWN"]
FraudBasis = Literal["manual_investigation", "customer_confirmation"]

_CONFIRMED_FRAUD_VALUES = {"CONFIRMED_FRAUD", "CONFIRMED_LEGITIMATE"}


def _reject_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("occurred_at must be timezone-aware")
    return value


class OrderStatusReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension: Literal["order_status"] = "order_status"
    value: OrderStatusValue
    occurred_at: datetime
    # Set explicitly by the merchant when reporting outside the normal window
    # — stored for the report to disclose, never itself a validation gate.
    late_report: bool = False
    # None for the first report on this dimension; the current head's
    # event_id for a correction. A mismatch is a conflict, not silently
    # accepted (P5's append-only rule).
    supersedes_event_id: str | None = None

    @field_validator("occurred_at")
    @classmethod
    def _tz_aware(cls, value: datetime) -> datetime:
        return _reject_naive(value)


class FraudAssessmentReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension: Literal["fraud_assessment"] = "fraud_assessment"
    value: FraudAssessmentValue
    # Required for CONFIRMED_FRAUD/CONFIRMED_LEGITIMATE, forbidden otherwise:
    # a payment dispute or a lack of feedback alone does not establish a
    # confirmed label, and the schema — not a convention — is what keeps a
    # weak basis off a confirmed value.
    basis: FraudBasis | None = None
    occurred_at: datetime
    late_report: bool = False
    supersedes_event_id: str | None = None

    @field_validator("occurred_at")
    @classmethod
    def _tz_aware(cls, value: datetime) -> datetime:
        return _reject_naive(value)

    @model_validator(mode="after")
    def _basis_matches_value(self) -> FraudAssessmentReport:
        needs_basis = self.value in _CONFIRMED_FRAUD_VALUES
        if needs_basis and self.basis is None:
            raise ValueError("basis is required when value is CONFIRMED_FRAUD or CONFIRMED_LEGITIMATE")
        if not needs_basis and self.basis is not None:
            raise ValueError("basis must be omitted unless value is CONFIRMED_FRAUD or CONFIRMED_LEGITIMATE")
        return self


OutcomeReportRequest = Annotated[
    OrderStatusReport | FraudAssessmentReport, Field(discriminator="dimension")
]


class OutcomeEventResponse(BaseModel):
    event_id: str
    chain_id: str
    dimension: str
    value: str
    basis: str | None = None
    occurred_at: str
    reported_at: str
    late_report: bool
    supersedes_event_id: str | None = None


class OutcomeTimelineResponse(BaseModel):
    chain_id: str
    current: dict[str, OutcomeEventResponse]
    timeline: list[OutcomeEventResponse]


# --- Expiring reviewer links (I13) ---


class ProofShareCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # A display label only, never proof of the viewer's identity or an access
    # control decision. Bounded, not free-form commentary.
    purpose: str = Field(..., min_length=1, max_length=120)
    ttl_seconds: int | None = Field(default=None, gt=0)


class ProofShareCreateResponse(BaseModel):
    share_id: str
    chain_id: str
    # Shown exactly once, in this response. Never returned by any other
    # endpoint and never logged.
    token: str
    purpose: str
    scope: str
    issued_at: str
    expires_at: str


class ProofShareAttestation(BaseModel):
    type: str
    share_id: str
    chain_id: str
    decision: str
    chain_grade: str | None
    source_payload_digest: str
    issued_at: str
    expires_at: str
    issuer_public_key: str
    signature: str
