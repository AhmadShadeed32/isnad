from __future__ import annotations

from app import announce, velocity
from app.chain.models import EvidenceLink
from app.config import settings
from app.domain.enums import API_LABEL, Action, Result
from app.policy.engine import get_engine
from app.registry.directory import get_directory

# Local evidence: what this service knows about a number before it spends a
# penny on the network. Both links below are produced in microseconds from
# state this service already holds, which is why they carry cost 0 and are
# never offered to the planner — there is no budget decision to make about
# evidence that is already in hand.

SOURCE = "local"


def _link(action: Action, result: Result, signal: str, detail: str) -> EvidenceLink:
    return EvidenceLink(
        step=0,  # stamped by the investigator
        action=action,
        api=API_LABEL[action],
        result=result,
        signal=signal,
        detail=detail,
        source=SOURCE,
        latency_ms=0,
    )


async def gather(
    caller_number: str,
    callee_number: str | None = None,
    claimed_identity: str = "",
) -> list[EvidenceLink]:
    """Registry and Verified Caller evidence for an inbound call.

    Ordered announcement-first because that is the only one of the two that can
    clear a caller. Everything the registry alone can say is either neutral or
    incriminating — by design, and see the zeroed deltas in policy.yaml.
    """
    directory = get_directory(str(settings.registry_path))
    entry = directory.lookup(caller_number)
    links: list[EvidenceLink] = []

    # Tier 2 CONTRIBUTES to the pattern it is judged against, exactly as Tier 1
    # does, and for the same reason: a campaign run entirely through
    # /v1/reverse-verify used to be invisible to CALLER_HIGH_VELOCITY, because
    # only the Tier 1 screen ever wrote a row. Recorded before the count is
    # read, so this call is inside the window it is measured against.
    #
    # A callee is required and not optional: "how many different people has this
    # number reached" cannot be asked without knowing who was reached.
    if callee_number:
        await velocity.record_async(caller_number, callee_number)

    high_velocity, observed, _ = await velocity.is_high_velocity_async(
        get_engine(str(settings.policy_path)), caller_number
    )
    if high_velocity:
        links.append(
            _link(
                Action.REGISTRY_CHECK,
                Result.FLAG,
                "CALLER_HIGH_VELOCITY",
                f"screened against {observed} different people in the window",
            )
        )

    announced = None
    if callee_number:
        # Consuming, like Tier 1. One announcement is worth ONE verification,
        # to one party, once. A read that did not spend a use let a party
        # replay somebody else's announcement into unlimited signed, publicly
        # fetchable TRUST_CALLER receipts for a bank's number.
        announced = await announce.find_async(caller_number, callee_number, consume=True)
    if announced is not None:
        links.append(
            _link(
                Action.CALL_ANNOUNCEMENT,
                Result.PASS,
                "CALL_PRE_ANNOUNCED",
                f"{announced.display_name} announced this call before placing it",
            )
        )

    if entry is None:
        links.append(
            _link(
                Action.REGISTRY_CHECK,
                Result.INFO,
                "REGISTRY_UNLISTED",
                "number is not in the institution registry",
            )
        )
        return links

    if not entry.outbound:
        links.append(
            _link(
                Action.REGISTRY_CHECK,
                Result.FLAG,
                "REGISTRY_INBOUND_ONLY",
                f"{entry.institution_name} never places calls from this number",
            )
        )
    elif directory.check_claim(claimed_identity, entry) is False:
        # `is False` and nothing looser. `check_claim` returns None whenever the
        # registry cannot tell, and `not None` is true — which would put
        # REGISTRY_CLAIM_MISMATCH (+1.5, and signed) into the chain of every
        # honest caller who described themselves in words this file has not
        # indexed. Only a claim that positively names a different institution.
        links.append(
            _link(
                Action.REGISTRY_CHECK,
                Result.FLAG,
                "REGISTRY_CLAIM_MISMATCH",
                f"this number belongs to {entry.institution_name}, "
                "which is not who the caller claims to be",
            )
        )
    elif announced is None:
        links.append(
            _link(
                Action.REGISTRY_CHECK,
                Result.INFO,
                "REGISTRY_MATCH_UNANNOUNCED",
                f"number belongs to {entry.institution_name}, but no call was "
                "announced — caller ID alone establishes nothing",
            )
        )
    return links
