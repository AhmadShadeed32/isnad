from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.deps import get_live_provider, key_from_bearer, owner_for, require_api_key
from app.api.rate_limit import limit_per_key
from app.config import settings
from app.domain.schemas import SessionCreateRequest, SessionResponse
from app.events import current_owner, mask_phone
from app.providers import mock as mock_provider
from app.session.manager import SessionQuotaExceeded, SessionRecord, sessions

router = APIRouter(prefix="/v1", tags=["sessions"], dependencies=[Depends(limit_per_key)])


def _to_response(rec: SessionRecord) -> SessionResponse:
    return SessionResponse(
        session_id=rec.id,
        status=rec.status.value,
        # Masked, as it already is on the SSE bus. The session response was the
        # one place a full number was handed back (S3), which made it the
        # cheapest thing for a leaked or borrowed key to harvest.
        phone_number=mask_phone(rec.phone_number),
        reason=rec.reason,
        created_at=rec.created_at.isoformat(),
        expires_at=rec.expires_at.isoformat(),
    )


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    req: SessionCreateRequest, _key: str = Depends(require_api_key)
) -> SessionResponse:
    """Open a trust session: keep watching SIM/device after the verdict."""
    # Reset any stale demo trip so the session starts clean. A no-op on the
    # nac path, where TRIPPED is never populated.
    mock_provider.untrip_swap(req.phone_number)
    # Gated on settings.provider, not on demo_mode (S4). It used to force the
    # mock whenever demo mode was on, even under ISNAD_PROVIDER=nac, while
    # /v1/verify honoured the provider — so one endpoint was live and the other
    # scripted with nothing to tell them apart. "Is this real?" needs one answer.
    provider = get_live_provider()
    try:
        rec = await sessions.create(
            req.phone_number,
            ttl_seconds=req.ttl_seconds,
            provider=provider,
        )
    except SessionQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "session_quota_exceeded", "message": str(exc)},
        ) from exc
    return _to_response(rec)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, _key: str = Depends(require_api_key)) -> SessionResponse:
    rec = sessions.get(session_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": "No such session"},
        )
    return _to_response(rec)


@router.delete("/sessions/{session_id}", response_model=SessionResponse)
async def end_session(session_id: str, _key: str = Depends(require_api_key)) -> SessionResponse:
    rec = await sessions.end(session_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": "No such session"},
        )
    return _to_response(rec)


@router.post("/sessions/{session_id}/simulate-swap")
async def simulate_swap(session_id: str, authorization: str = Header(default="")) -> dict:
    """Demo control: inject a mid-session SIM swap on this session's number.

    Unauthenticated on purpose (stage demo). Only affects the mock provider;
    on a real network the monitor detects genuine swaps.

    Behind a key since S4, and the owner it resolves is also what lets it find
    the session at all, since sessions are scoped to their creator (S3). It no
    longer echoes the phone number back: it was the last route returning an
    unmasked one (S13).
    """
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "demo_disabled"})
    key = key_from_bearer(authorization)
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_api_key", "message": "Bearer API key required"},
        )
    current_owner.set(owner_for(key))
    rec = sessions.get(session_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": "No such session"},
        )
    mock_provider.trip_swap(rec.phone_number)
    return {"ok": True, "message": f"SIM swap injected for {mask_phone(rec.phone_number)}"}
