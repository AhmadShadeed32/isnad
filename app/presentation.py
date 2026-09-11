"""A deterministic, plain-language projection of an already-signed Verdict.

P2: a first-time merchant should be able to read
"Additional verification needed" and a short list of facts, without decoding
CHALLENGE / DEGRADED / 0.242 first. This module never does that decoding for
them by inventing anything: every sentence here is either

  (a) a fixed template string chosen only from `decision` / `chain_grade`, or
  (b) `f"{link.api}: {link.detail}"` for a link that is actually in the chain,
      where `link.detail` itself comes only from app/providers/vocabulary.py.

No LLM call, no operator free text, no I/O, no randomness. `present()` is a
pure function of the `Verdict` it is given: it does not import app.config or
app.policy.engine, so it can never quietly compare an old chain against
*today's* policy thresholds -- only against whatever `policy_snapshot` that
chain itself carries (or nothing, for a chain signed before that field
existed). This is what makes it safe to recompute on every read rather than
only at issuance time: the signed Verdict is immutable, so re-deriving the
same Presentation from it twice always agrees, and never "backfills" a
decision using a policy that was not the one in force when it was made.

Never touches `Verdict` or `EvidenceLink`, never re-signs, never calls
store.save. Purely additive: `VerificationResponse.presentation` is optional
and this module has no opinion about routes, caching or persistence.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.chain.models import CorroborationGap, EvidenceLink, Verdict
from app.domain.enums import API_LABEL, GRADE_MEANING, Action, ChainGrade, Decision, Result

# How many facts of each kind to show. A merchant reading this is not auditing
# the chain -- app/static/judge.html's evidence trace already shows every link
# with its own provenance -- so this is a summary, not a duplicate ledger.
MAX_FACTS = 5

# The three signals that mean "the network could not answer", as opposed to
# "the network answered and it was fine" (an INFO result like LOCATION_UNKNOWN
# or ROAMING_NETWORK is still an answer). Mirrors
# app/agent/investigator.py's _UNRESOLVED_SIGNALS -- duplicated rather than
# imported so this module never depends on the investigator's internals, only
# on the same public vocabulary both already agree on.
_UNRESOLVED_SIGNALS = frozenset({"CONSENT_REQUIRED", "PROVIDER_UNAVAILABLE", "EVIDENCE_UNAVAILABLE"})

# Why a required corroborating check did not answer. Keyed off the bounded
# `CorroborationGap.reason` vocabulary, never provider prose, and phrased so a
# merchant can tell "we could not finish the check" apart from "the check
# found something".
_GAP_REASON: dict[str, str] = {
    "unresolved": (
        "they were requested and the network could not answer them"
    ),
    "budget": "the evidence budget for this request did not cover them",
    "unavailable": (
        "they need information this request did not include, so no operator "
        "call was possible"
    ),
    "not_attempted": "the investigation ended before they were requested",
}


_TITLE: dict[Decision, str] = {
    Decision.ALLOW: "Proceed",
    Decision.CHALLENGE: "Additional verification needed",
    Decision.DECLINE: "Do not proceed",
}

_NEXT_ACTION: dict[Decision, str] = {
    Decision.ALLOW: "No further action needed. You may proceed with this order.",
    Decision.CHALLENGE: (
        "Ask the customer to complete your own additional verification step, "
        "such as a callback or manual review, before proceeding. Isnad has not "
        "sent the customer a one-time code: this decision means more evidence "
        "is needed, not that a code is waiting to be entered."
    ),
    Decision.DECLINE: "Do not proceed with this order without independent manual review.",
}


class Presentation(BaseModel):
    """What a first-time visitor sees. Never signed, never part of `Verdict`,
    safe to regenerate from the same Verdict at any time."""

    title: str
    summary: str
    supporting_facts: list[str] = Field(default_factory=list)
    adverse_facts: list[str] = Field(default_factory=list)
    # Named separately from adverse_facts: an unresolved check is not evidence
    # against the customer, it is a hole in the chain (see GRADE_MEANING's
    # UNRESOLVED entry). Collapsing the two would tell a merchant the network
    # found something adverse when it actually found nothing at all.
    unresolved_checks: list[str] = Field(default_factory=list)
    # Adverse findings the agent could not corroborate. Distinct from
    # `unresolved_checks`, which names checks that came back empty: this names
    # a FINDING that stands unconfirmed, which is the reason the decision is a
    # CHALLENGE rather than the DECLINE the raw score alone would have given.
    # Empty for every chain signed before the gate existed, so nothing may read
    # an empty list as proof the gate ran.
    unmet_corroboration: list[str] = Field(default_factory=list)
    next_action: str


def _fact(link: EvidenceLink) -> str:
    """One human sentence for a link, traceable to that exact link.

    `link.api` and `link.detail` are both already-reviewed vocabulary (see
    app/providers/vocabulary.py's module docstring): this function adds no
    words of its own, so no fact here can say more than the chain does. In
    particular it never converts a `max_age_hours` window into an inferred
    event age -- `link.detail` already states the window, and that is the
    strongest true statement available.
    """
    return f"{link.api}: {link.detail}"


def _gap_sentence(gap: CorroborationGap, verdict: Verdict) -> str:
    """One sentence per uncorroborated finding, built only from the signed gap
    and the chain it came from. Adds no judgement of its own."""
    finding = next(
        (link.api for link in verdict.chain if link.signal == gap.signal), gap.signal
    )
    required = ", ".join(_api_label(name) for name in gap.required) or "no check"
    reason = _GAP_REASON.get(gap.reason, "they did not complete")
    return (
        f"{finding}: this finding was not corroborated. "
        f"{required} could have confirmed or cleared it, and {reason}."
    )


def _api_label(action_id: str) -> str:
    """The human CAMARA label for an action id, or the id itself if it is not
    one this build knows — never a guess."""
    try:
        return API_LABEL[Action(action_id)]
    except (ValueError, KeyError):
        return action_id


def _degraded_context(verdict: Verdict) -> str | None:
    """The one extra, still-derived-not-invented sentence for the DEGRADED
    CHALLENGE case (Act VI-shaped): the score, and the very thresholds the
    signed chain itself carries. Omitted, not defaulted to today's policy,
    when an older chain carries no `policy_snapshot`."""
    allow_below = verdict.policy_snapshot.get("allow_below")
    decline_above = verdict.policy_snapshot.get("decline_above")
    if not isinstance(allow_below, (int, float)) or not isinstance(decline_above, (int, float)):
        return None
    return (
        f"The policy snapshot this decision was made under allows automatically "
        f"at or below {allow_below:g} and declines automatically at or above "
        f"{decline_above:g}. This case's uncalibrated policy score of "
        f"{verdict.confidence:g} falls between them."
    )


def _summary(verdict: Verdict, unresolved_checks: list[str], gaps: list[str]) -> str:
    grade = verdict.chain_grade
    if grade is None:
        base = "This chain was issued before chain grading existed, so no grade was signed for it."
    else:
        # GRADE_MEANING is an internal, reviewed constant (app/domain/enums.py),
        # not free text -- reusing it means this sentence was already vetted
        # for the same audience T3's narrative and T4's answers serve.
        meaning = GRADE_MEANING[grade.value]
        if grade == ChainGrade.DEGRADED and not any(
            link.result == Result.FLAG for link in verdict.chain
        ):
            # DEGRADED covers two different situations, and the shared sentence
            # only describes one of them. It is accurate when an adverse signal
            # was found and left uncorroborated. It is simply FALSE when every
            # link came back clean and the score merely landed mid-band —
            # which is exactly what a two-check run on a stable subscriber
            # produces, and what a judge sees on the paired demonstration's
            # clean case. Telling a merchant that evidence "came back adverse"
            # when none did is the one kind of error this project exists to
            # not make, so this states what actually happened instead.
            meaning = (
                "the links resolved and none of them contradicted the claim, but "
                "there were too few of them to settle it"
            )
        base = meaning[0].upper() + meaning[1:] + "."

    pieces = [base]

    # Said before anything about the score, and it replaces the DEGRADED
    # "the score simply landed in an uncertain range" sentence below rather
    # than sitting beside it: that sentence describes an agent that finished
    # its work and was unsure, and this one describes an agent that could not
    # finish. Both cannot be true of the same run.
    if gaps:
        pieces.extend(gaps)
        pieces.append(
            "The decision is a request for another verification step rather "
            "than a refusal, because the adverse finding above was never "
            "confirmed."
        )
        return " ".join(pieces)

    if grade == ChainGrade.UNRESOLVED:
        if unresolved_checks:
            pieces.append(
                "Specifically, the following could not be obtained: "
                + "; ".join(unresolved_checks)
                + "."
            )
        elif verdict.chain:
            # A required link came back, nothing contradicted the claim, and
            # yet the chain is still graded UNRESOLVED: by construction (see
            # app/policy/engine.py's grade()) that only happens when the chain
            # lacked enough independently corroborating network evidence, not
            # because any one check failed. Naming a specific failed check here
            # would be a guess this module has no basis for, so it says the
            # weaker, still-true thing instead.
            pieces.append(
                "No single check failed here. The chain did not contain enough "
                "independently corroborating network evidence to clear this "
                "automatically."
            )
        else:
            pieces.append("No evidence was gathered before this decision.")
    elif grade == ChainGrade.DEGRADED and verdict.decision == Decision.CHALLENGE:
        pieces.append(
            "This is not a failed identity check and not a case of withheld "
            "consent. The available evidence was gathered and reviewed; the "
            "resulting risk score simply landed in a range this policy treats "
            "as uncertain, which calls for one more verification step."
        )
        context = _degraded_context(verdict)
        if context:
            pieces.append(context)

    return " ".join(pieces)


def present(verdict: Verdict) -> Presentation:
    """Project a signed Verdict into a plain-language Presentation.

    Pure function: reads only fields already inside `verdict` (decision,
    chain_grade, chain, confidence, policy_snapshot). Never calls the live
    policy engine, never re-decides anything, never mutates `verdict`.
    """
    supporting = [_fact(link) for link in verdict.chain if link.result == Result.PASS]
    adverse = [_fact(link) for link in verdict.chain if link.result == Result.FLAG]
    unresolved = [_fact(link) for link in verdict.chain if link.signal in _UNRESOLVED_SIGNALS]
    gaps = [_gap_sentence(gap, verdict) for gap in verdict.unmet_corroboration]

    return Presentation(
        title=_TITLE.get(verdict.decision, verdict.decision.value),
        summary=_summary(verdict, unresolved[:MAX_FACTS], gaps[:MAX_FACTS]),
        supporting_facts=supporting[:MAX_FACTS],
        adverse_facts=adverse[:MAX_FACTS],
        unresolved_checks=unresolved[:MAX_FACTS],
        unmet_corroboration=gaps[:MAX_FACTS],
        next_action=_NEXT_ACTION.get(
            verdict.decision,
            "Contact support: this decision does not carry a recognized action.",
        ),
    )
