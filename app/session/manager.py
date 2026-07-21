from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.domain.enums import Action, Result, SessionStatus
from app.domain.schemas import RequestContext, VerificationRequest
from app.events import emit
from app.providers import get_provider
from app.providers.base import EvidenceProvider


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SessionRecord:
    id: str
    phone_number: str
    status: SessionStatus
    created_at: datetime
    expires_at: datetime
    reason: Optional[str] = None
    task: Optional[asyncio.Task] = field(default=None, repr=False)


class SessionManager:
    """Trust-with-a-TTL. After a verdict, keep watching the SIM/device; if either
    changes mid-session, revoke the session live.

    In production the monitor is a subscription to CAMARA change-notifications;
    here it polls the provider on an interval — same effect, simpler to run.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}

    def get(self, session_id: str) -> Optional[SessionRecord]:
        return self._sessions.get(session_id)

    async def create(
        self,
        phone_number: str,
        ttl_seconds: Optional[int] = None,
        poll_seconds: Optional[float] = None,
        provider: Optional[EvidenceProvider] = None,
    ) -> SessionRecord:
        ttl = ttl_seconds if ttl_seconds is not None else settings.session_ttl_seconds
        poll = poll_seconds if poll_seconds is not None else settings.session_poll_seconds
        now = _now()
        rec = SessionRecord(
            id="ses_" + uuid.uuid4().hex[:20],
            phone_number=phone_number,
            status=SessionStatus.ACTIVE,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )
        self._sessions[rec.id] = rec
        await self._emit(rec, "started")
        rec.task = asyncio.create_task(self._monitor(rec, poll, provider or get_provider()))
        return rec

    async def end(self, session_id: str) -> Optional[SessionRecord]:
        rec = self._sessions.get(session_id)
        if rec is None:
            return None
        if rec.status == SessionStatus.ACTIVE:
            rec.status = SessionStatus.ENDED
            rec.reason = "ended by caller"
            if rec.task:
                rec.task.cancel()
            await self._emit(rec, "ended")
        return rec

    async def shutdown(self) -> None:
        for rec in self._sessions.values():
            if rec.task and not rec.task.done():
                rec.task.cancel()

    async def _monitor(self, rec: SessionRecord, poll: float, provider: EvidenceProvider) -> None:
        req = VerificationRequest(
            phone_number=rec.phone_number,
            context=RequestContext(event="session_monitor"),
        )
        try:
            while rec.status == SessionStatus.ACTIVE:
                if _now() >= rec.expires_at:
                    rec.status = SessionStatus.EXPIRED
                    rec.reason = "TTL reached"
                    await self._emit(rec, "expired")
                    return
                await asyncio.sleep(poll)
                if rec.status != SessionStatus.ACTIVE:
                    return
                sim = await provider.gather(Action.SIM_SWAP, req)
                dev = await provider.gather(Action.DEVICE_SWAP, req)
                flag = next((lk for lk in (sim, dev) if lk.result == Result.FLAG), None)
                if flag is not None:
                    rec.status = SessionStatus.REVOKED
                    rec.reason = f"{flag.api}: {flag.detail}"
                    await self._emit(rec, "revoked")
                    return
        except asyncio.CancelledError:  # pragma: no cover
            return

    async def _emit(self, rec: SessionRecord, event: str) -> None:
        await emit(
            {
                "type": "session",
                "event": event,
                "session_id": rec.id,
                "status": rec.status.value,
                "phone_number": rec.phone_number,
                "reason": rec.reason,
            }
        )


# Module-level singleton shared by routes, console, and tests.
sessions = SessionManager()
