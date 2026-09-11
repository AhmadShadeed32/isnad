from __future__ import annotations

import time

from app import announce, velocity
from app.config import settings
from app.domain.schemas import ScreenResponse
from app.policy.engine import get_engine
from app.registry.directory import get_directory

# Tier 1 labels. One place decides them, because the console act and the public
# endpoint must never disagree about what a call was called — a demo that shows
# a different answer from the API is worse than no demo.
LABEL_VERIFIED = "VERIFIED_INSTITUTION"
LABEL_SUSPECTED_SPOOF = "SUSPECTED_SPOOF"
LABEL_UNKNOWN = "UNKNOWN"

# Every label the API can produce. console.html must define a CSS rule for each:
# Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER against a
# stylesheet that only knew ALLOW/CHALLENGE/DECLINE, so the verdict panel stayed
# grey whatever the answer was. A test pins this list against the stylesheet.
LABELS = (LABEL_VERIFIED, LABEL_SUSPECTED_SPOOF, LABEL_UNKNOWN)


async def screen_call(
    caller_number: str, callee_number: str, claimed_identity: str = ""
) -> ScreenResponse:
    """Tier 1 — local state only, no network call.

    The honest majority answer is UNKNOWN and it stays UNKNOWN: a registry hit
    on its own is NOT a reason to trust a caller, because caller ID is spoofable
    and a scammer presenting the bank's real number produces exactly the same
    hit. Only an announcement — which required proving who you were — produces
    VERIFIED_INSTITUTION.
    """
    t0 = time.perf_counter()
    directory = get_directory(str(settings.registry_path))
    entry = directory.lookup(caller_number)
    engine = get_engine(str(settings.policy_path))

    # Recorded before the answer is computed, so this call counts toward the
    # pattern it is being judged against. A campaign's 400th call should see the
    # first 399.
    await velocity.record_async(caller_number, callee_number)
    high_velocity, observed, threshold = await velocity.is_high_velocity_async(
        engine, caller_number
    )

    label, reason, basis = LABEL_UNKNOWN, "", "no_local_evidence"
    institution_name = entry.institution_name if entry else None

    # Consuming: this IS the screening decision for this call.
    announced = await announce.find_async(caller_number, callee_number, consume=True)
    if high_velocity and announced is None:
        # Ordered above every registry branch on purpose. A number reaching this
        # many different people in the window is a campaign whatever the
        # registry says about it — and a spoofed campaign wearing a real
        # institution's number would otherwise land on the reassuring
        # "belongs to Demo Bank" branch.
        #
        # An announcement still wins: an institution that told us it was calling
        # and proved who it was is allowed to call a lot of people.
        label = LABEL_SUSPECTED_SPOOF
        basis = "caller_velocity"
        reason = (
            f"This number has been screened against {observed} different people "
            f"in the last {engine.velocity_window() // 60} minutes "
            f"(flagged at {threshold}). No single call looks wrong; the pattern does."
        )
    elif announced is not None:
        label = LABEL_VERIFIED
        basis = "pre_announcement"
        institution_name = announced.display_name or institution_name
        reason = (
            f"{institution_name} announced this call before placing it, "
            "from a key bound to that institution."
        )
    elif entry is not None and not entry.outbound:
        label = LABEL_SUSPECTED_SPOOF
        basis = "registry_inbound_only"
        reason = (
            f"{entry.institution_name} publishes this number for customers to "
            "call in on and never places calls from it."
        )
    elif entry is not None and directory.check_claim(claimed_identity, entry) is False:
        # `is False`, never `not ...`: None means the registry cannot tell, and
        # falling through to SUSPECTED_SPOOF on "cannot tell" labels honest
        # callers as spoofed for naming a department.
        label = LABEL_SUSPECTED_SPOOF
        basis = "registry_claim_mismatch"
        reason = "The caller's claim does not match the institution that owns this number."
    elif entry is not None:
        # The number is the institution's and nothing contradicts it — but
        # nothing confirms it either. Saying "verified" here would be the whole
        # bug: it is exactly what a spoofed call looks like.
        basis = "registry_match_unannounced"
        reason = (
            f"This number belongs to {entry.institution_name}, but no call was "
            "announced. Caller ID alone does not establish who is calling."
        )
    else:
        reason = "This number is not in the registry, which is not evidence either way."

    return ScreenResponse(
        label=label,
        reason=reason,
        caller_number=caller_number,
        institution_name=institution_name,
        basis=basis,
        elapsed_us=int((time.perf_counter() - t0) * 1e6),
    )
