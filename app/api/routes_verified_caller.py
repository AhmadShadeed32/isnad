from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app import announce
from app.api.deps import require_api_key
from app.api.rate_limit import limit_per_key, limit_screen
from app.config import settings
from app.domain.schemas import (
    PreAnnounceRequest,
    PreAnnounceResponse,
    ScreenRequest,
    ScreenResponse,
)
from app.registry.directory import get_directory
from app.screening import screen_call

# Limiters are per-route here, not router-wide: pre-announce is a low-volume
# institutional call and screening is the opposite.
router = APIRouter(prefix="/v1", tags=["verified-caller"])

# CAMARA VerifiedCaller, answered locally.
#
# No CAMARA API can attest a PBX call: SIM Swap, Number Verification, Device
# Swap, Reachability, Roaming and Location Verification are all facts about a
# MOBILE SUBSCRIPTION, and a bank's SIP trunk has no SIM. The standard's answer
# is to invert the question — rather than interrogating the call, the institution
# announces it from an authenticated channel, and the callee's check asks whether
# a matching announcement exists.
#
# The standard exists; the service does not. VerifiedCaller is at CAMARA's
# Sandbox tier with one release and zero commercial operator launches anywhere,
# and it is not among the APIs Nokia Network as Code exposes. So this endpoint
# implements the published contract against local state. It must never be
# described as an operator attestation, because no operator is involved.


def _directory():
    return get_directory(str(settings.registry_path))


@router.post(
    "/verified-caller/pre-announce",
    response_model=PreAnnounceResponse,
    dependencies=[Depends(limit_per_key)],
)
async def pre_announce(
    req: PreAnnounceRequest,
    key: str = Depends(require_api_key),
) -> PreAnnounceResponse:
    """An institution declaring a call it is about to place.

    Two things are checked, and both have to hold. The key must be BOUND to an
    institution, and the number being called from must belong to that same
    institution in the registry. Either one alone is the hole: a bound key with
    no number check could announce calls from any bank's number, and a number
    check with no binding would let anyone announce anything.

    The institution is taken from the key, never from the body.
    """
    institution_id = announce.institution_for_key(key)
    if institution_id is None:
        # Fails closed and says why without naming what would have worked.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "not_an_institution",
                "message": "This key is not bound to an institution",
            },
        )

    entry = _directory().lookup(req.calling_participant)
    if entry is None or entry.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "number_not_yours",
                "message": "That number is not registered to this institution",
            },
        )
    if not entry.outbound:
        # A published inbound-only line. The institution's own registry entry
        # says it never originates calls, so announcing one from it is either a
        # stale entry or a compromised key — and letting it through would make
        # the strongest spoof signal in the system verify itself.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "inbound_only_number",
                "message": "That number is published as one you never call from",
            },
        )

    announcement_id, expires_at = await announce.record_async(
        institution_id=institution_id,
        api_key=key,
        calling_participant=req.calling_participant,
        called_participant=req.called_participant,
        strategy=req.strategy,
        display_name=req.dynamic_display_name or entry.institution_name,
        call_reason=req.call_reason,
        time_to_live=req.time_to_live,
    )
    return PreAnnounceResponse(
        announcement_id=announcement_id,
        institution_id=institution_id,
        strategy=req.strategy,
        expires_at=expires_at,
        time_to_live_seconds=announce._ttl_seconds(req.time_to_live),
    )


@router.post("/screen", response_model=ScreenResponse, dependencies=[Depends(limit_screen)])
async def screen(
    req: ScreenRequest,
    _key: str = Depends(require_api_key),
) -> ScreenResponse:
    """Tier 1 — the pre-ring check. Local state only, no network call.

    This exists because the full chain cannot run in the time a phone rings.
    Observed CAMARA latencies are 346-863ms per call and the agent gathers
    sequentially by design, so a real chain is well over a second before
    anything can be shown. This path is a dict lookup and one indexed row.

    "Pre-ring" is the latency budget, not a claim about a shipped client. No
    on-device screening app exists: Android CallScreeningService and iOS Live
    Caller ID Lookup are recorded as future work and were deliberately cut. The
    consumers of this endpoint today are the console and the API.

    The label rules live in app/screening.py so the console act and this
    endpoint cannot drift apart.
    """
    return await screen_call(req.caller_number, req.callee_number, req.claimed_identity)
