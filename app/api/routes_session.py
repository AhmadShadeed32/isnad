from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_live_provider, require_api_key
from app.config import settings
from app.domain.schemas import SessionCreateRequest, SessionResponse
from app.providers import mock as mock_provider
from app.providers.mock import MockProvider
from app.session.manager import SessionRecord, sessions

router = APIRouter(prefix="/v1", tags=["sessions"])


def _to_response(rec: SessionRecord) -> SessionResponse:
    return SessionResponse(
        session_id=rec.id,
        status=rec.status.value,
        phone_number=rec.phone_number,
        reason=rec.reason,
        created_at=rec.created_at.isoformat(),
        expires_at=rec.expires_at.isoformat(),
    )


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    req: SessionCreateRequest, _key: str = Depends(require_api_key)
) -> SessionResponse:
    """Open a trust session: keep watching SIM/device after the verdict."""
    # Reset any stale demo trip so the session starts clean.
    mock_provider.untrip_swap(req.phone_number)
    provider = MockProvider() if settings.demo_mode else get_live_provider()
    rec = await sessions.create(
        req.phone_number,
        ttl_seconds=req.ttl_seconds,
        provider=provider,
    )
    return _to_response(rec)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, _key: str = Depends(require_api_key)) -> SessionResponse:
    rec = sessions.get(session_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"code": "session_not_found", "message": session_id})
    return _to_response(rec)


@router.delete("/sessions/{session_id}", response_model=SessionResponse)
async def end_session(session_id: str, _key: str = Depends(require_api_key)) -> SessionResponse:
    rec = await sessions.end(session_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"code": "session_not_found", "message": session_id})
    return _to_response(rec)


@router.post("/sessions/{session_id}/simulate-swap")
async def simulate_swap(session_id: str) -> dict:
    """Demo control: inject a mid-session SIM swap on this session's number.

    Unauthenticated on purpose (stage demo). Only affects the mock provider;
    on a real network the monitor detects genuine swaps.
    """
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "demo_disabled"})
    rec = sessions.get(session_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"code": "session_not_found", "message": session_id})
    mock_provider.trip_swap(rec.phone_number)
    return {"ok": True, "message": f"SIM swap injected for {rec.phone_number}"}
