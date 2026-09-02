from __future__ import annotations

import asyncio
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.config import makes_billable_calls, settings
from app.domain.enums import Action, Result, SessionStatus
from app.domain.schemas import RequestContext, VerificationRequest
from app.events import current_owner, emit
from app.ownership import ANONYMOUS
from app.providers import get_provider
from app.providers import mock as mock_provider
from app.providers.base import EvidenceProvider


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class SessionRecord:
    id: str
    phone_number: str
    status: SessionStatus
    created_at: datetime
    expires_at: datetime
    reason: str | None = None
    # sha256 of the API key that opened the session. Reads and deletes filter on
    # it: without it any key could read — and end — any other key's session, and
    # the response carried an unmasked phone number with it (S3).
    owner_hash: str = ANONYMOUS
    task: asyncio.Task | None = field(default=None, repr=False)


class SessionQuotaExceeded(RuntimeError):
    """This owner already has as many live sessions as it is allowed."""


class SessionManager:
    """Trust-with-a-TTL. After a verdict, keep watching the SIM/device; if either
    changes mid-session, revoke the session live.

    In production the monitor is a subscription to CAMARA change-notifications;
    here it polls the provider on an interval — same effect, simpler to run.

    Every knob that decides how many provider calls a single request can cause is
    bounded here (S7a). Unbounded, one request with ttl_seconds=86400 polled SIM
    Swap and Device Swap every 1.5s for a day: 115,200 billed CAMARA calls, with
    no concurrency cap and no per-key quota.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}

    def _live_for(self, owner: str) -> int:
        return sum(
            1
            for rec in self._sessions.values()
            if rec.status == SessionStatus.ACTIVE and rec.owner_hash == owner
        )

    def _prune(self) -> None:
        """Drop terminal records. `_sessions` was never pruned."""
        for session_id, rec in list(self._sessions.items()):
            if rec.status != SessionStatus.ACTIVE and (rec.task is None or rec.task.done()):
                del self._sessions[session_id]

    def get(self, session_id: str) -> SessionRecord | None:
        """A session the current caller owns, or None.

        None rather than a distinct error, so a session id cannot be probed for
        existence by a key that does not own it.
        """
        rec = self._sessions.get(session_id)
        if rec is None:
            return None
        if not secrets.compare_digest(rec.owner_hash, current_owner.get() or ANONYMOUS):
            return None
        return rec

    async def create(
        self,
        phone_number: str,
        ttl_seconds: int | None = None,
        poll_seconds: float | None = None,
        provider: EvidenceProvider | None = None,
    ) -> SessionRecord:
        ttl = ttl_seconds if ttl_seconds is not None else settings.session_ttl_seconds
        ttl = min(ttl, settings.session_max_ttl_seconds)
        poll = poll_seconds if poll_seconds is not None else settings.session_poll_seconds
        if makes_billable_calls(settings):
            # A 1.5s poll against a billed API is a quota amplifier, not a
            # feature. This includes the selective-live hybrid path; the floor
            # is only skipped when no provider action can leave the process.
            poll = max(poll, settings.session_min_poll_seconds_nac)
        owner = current_owner.get() or ANONYMOUS

        self._prune()
        if self._live_for(owner) >= settings.session_max_per_owner:
            raise SessionQuotaExceeded(
                f"at most {settings.session_max_per_owner} concurrent sessions per key"
            )

        now = _now()
        rec = SessionRecord(
            id="ses_" + uuid.uuid4().hex[:20],
            phone_number=phone_number,
            status=SessionStatus.ACTIVE,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            owner_hash=owner,
        )
        self._sessions[rec.id] = rec
        await self._emit(rec, "started")
        rec.task = asyncio.create_task(self._monitor(rec, poll, provider or get_provider()))
        return rec

    async def end(self, session_id: str) -> SessionRecord | None:
        rec = self.get(session_id)
        if rec is None:
            return None
        if rec.status == SessionStatus.ACTIVE:
            rec.status = SessionStatus.ENDED
            rec.reason = "ended by caller"
            if rec.task:
                rec.task.cancel()
            # `TRIPPED` is a mock-only stage affordance, but it is module
            # state. The session demo uses Act I's number, so retaining it
            # makes the next full run start its clean signup with a fabricated
            # SIM swap. Clearing is harmless on the live-provider path.
            mock_provider.untrip_swap(rec.phone_number)
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
                    mock_provider.untrip_swap(rec.phone_number)
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
                    mock_provider.untrip_swap(rec.phone_number)
                    await self._emit(rec, "revoked")
                    return
        except asyncio.CancelledError:  # pragma: no cover
            return
        except Exception:  # noqa: BLE001 - the monitor must fail closed for every error
            # A monitor that crashes while the session stays ACTIVE creates a
            # false statement of continuing trust. Fail closed and make the
            # conservative revocation visible to the same stream as a signal.
            if rec.status == SessionStatus.ACTIVE:
                rec.status = SessionStatus.REVOKED
                rec.reason = "session monitor failed; trust revoked"
                mock_provider.untrip_swap(rec.phone_number)
                await self._emit(rec, "revoked")

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
