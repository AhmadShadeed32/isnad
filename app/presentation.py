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

from app.chain.models import EvidenceLink, Verdict
from app.domain.enums import GRADE_MEANING, ChainGrade, Decision, Result

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


def _summary(verdict: Verdict, unresolved_checks: list[str]) -> str:
    grade = verdict.chain_grade
    if grade is None:
        base = "This chain was issued before chain grading existed, so no grade was signed for it."
    else:
        # GRADE_MEANING is an internal, reviewed constant (app/domain/enums.py),
        # not free text -- reusing it means this sentence was already vetted
        # for the same audience T3's narrative and T4's answers serve.
        meaning = GRADE_MEANING[grade.value]
        base = meaning[0].upper() + meaning[1:] + "."

    pieces = [base]

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

    return Presentation(
        title=_TITLE.get(verdict.decision, verdict.decision.value),
        summary=_summary(verdict, unresolved[:MAX_FACTS]),
        supporting_facts=supporting[:MAX_FACTS],
        adverse_facts=adverse[:MAX_FACTS],
        unresolved_checks=unresolved[:MAX_FACTS],
        next_action=_NEXT_ACTION.get(
            verdict.decision,
            "Contact support: this decision does not carry a recognized action.",
        ),
    )
