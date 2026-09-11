from __future__ import annotations

from enum import Enum


class Decision(str, Enum):
    ALLOW = "ALLOW"
    CHALLENGE = "CHALLENGE"
    DECLINE = "DECLINE"


class ChainGrade(str, Enum):
    """How much the evidence chain itself was worth, independent of the decision.

    The decision says what the caller should DO; the grade says what the chain
    WAS. The pair that matters most is UNRESOLVED vs DEGRADED: "we could not
    check" and "the check failed" are different facts, and collapsing them is
    what manufactures false declines.

    Comparable to STIR/SHAKEN attestation levels (A/B/C) for caller ID, applied
    to the whole identity chain rather than the calling number alone.
    """

    ATTESTED_FULL = "ATTESTED_FULL"  # every link resolved and corroborating
    ATTESTED_PARTIAL = "ATTESTED_PARTIAL"  # resolved, nothing contradicts, thin corroboration
    UNRESOLVED = "UNRESOLVED"  # a required link could not be obtained
    DEGRADED = "DEGRADED"  # links resolved, one or more adverse
    REFUTED = "REFUTED"  # a link directly contradicts the claim


# What each grade means, in one sentence, for anything that has to explain a
# verdict in English (T3's narrative, T4's answers).
#
# These are internal constants, not free text, so passing them into a prompt
# respects the injection boundary. They exist because a model given only the bare
# enum name guesses at it — and guesses wrong: asked to narrate a REFUTED chain,
# it wrote "the hypothesis was refuted overall" alongside a high fraud
# probability and a decline, which is self-contradictory. The grade describes
# what happened to the CUSTOMER'S CLAIM, not to the fraud hypothesis.
GRADE_MEANING: dict[str, str] = {
    ChainGrade.ATTESTED_FULL.value: "every evidence link resolved and corroborated the customer's claim",
    ChainGrade.ATTESTED_PARTIAL.value: "the links resolved and nothing contradicted the claim, but corroboration was thin",
    ChainGrade.UNRESOLVED.value: "a required link could not be obtained at all — consent withheld, the "
    "provider was dark, or no evidence was gathered at all. This is 'we "
    "could not check', NOT 'the check failed'",
    ChainGrade.DEGRADED.value: "the links resolved and one or more came back adverse to the claim",
    ChainGrade.REFUTED.value: "an evidence link directly contradicted the customer's claim — the claim "
    "is refuted, which means fraud is supported, not ruled out",
}


class Result(str, Enum):
    PASS = "PASS"
    FLAG = "FLAG"
    INFO = "INFO"  # informational / could-not-determine


class Action(str, Enum):
    """The evidence-gathering moves available to the agent.

    Each maps to one CAMARA API, except `step_up_otp`, which maps to nothing
    here: an OTP is the merchant's to send, in a channel this service does not
    own, and no code path gathers it. It stays in the vocabulary because the
    counterfactual and the policy price it — a decision the agent chose NOT to
    take is still a decision worth naming — but nothing selects it.
    """

    NUMBER_VERIFY = "number_verify"
    SIM_SWAP = "sim_swap"
    DEVICE_SWAP = "device_swap"
    LOCATION_VERIFY = "location_verify"
    REACHABILITY = "reachability"
    ROAMING = "roaming"
    DEVICE_INTELLIGENCE = "device_intelligence"
    # Has the subscriber behind this number changed since the merchant last
    # verified it? Only answerable when the merchant actually holds that date,
    # so this action has a precondition like location_verify does.
    NUMBER_RECYCLING = "number_recycling"
    STEP_UP_OTP = "step_up_otp"
    # Local evidence, not CAMARA calls and not planner choices: both are answered
    # from this service's own state in microseconds, before any network call is
    # made. They are excluded from the planner's candidate set for that reason —
    # there is nothing to decide about spending budget you do not spend.
    REGISTRY_CHECK = "registry_check"
    CALL_ANNOUNCEMENT = "call_announcement"


# Human-readable CAMARA API label for each action (rendered in the chain).
API_LABEL: dict[Action, str] = {
    Action.NUMBER_VERIFY: "Number Verification",
    Action.SIM_SWAP: "SIM Swap",
    Action.DEVICE_SWAP: "Device Swap",
    Action.LOCATION_VERIFY: "Location Verification",
    Action.REACHABILITY: "Device Reachability Status",
    Action.ROAMING: "Device Roaming Status",
    Action.DEVICE_INTELLIGENCE: "Device Intelligence",
    Action.NUMBER_RECYCLING: "Number Recycling",
    Action.STEP_UP_OTP: "Step-up (OTP)",
    Action.REGISTRY_CHECK: "Number Registry",
    Action.CALL_ANNOUNCEMENT: "Verified Caller pre-announce",
}


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"  # trust is live; signals are being watched
    REVOKED = "REVOKED"  # a mid-session SIM/device change killed it
    ENDED = "ENDED"  # ended by the caller
    EXPIRED = "EXPIRED"  # TTL reached


class Hypothesis(str, Enum):
    ACCOUNT_TAKEOVER = "account_takeover"
    MULE = "mule"
    BOT_FARM = "bot_farm"
    LEGIT = "legit"
    LEGIT_THIN_FILE = "legit_thin_file"
    # Reverse Isnad: is an inbound *caller* who they claim to be?
    IMPERSONATION = "impersonation"
