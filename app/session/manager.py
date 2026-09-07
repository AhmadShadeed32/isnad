from __future__ import annotations

import asyncio
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.config import makes_billable_calls, settings
from app.domain.enums import Action, Result, SessionStatus
from app.domain.schemas import RequestContext, VerificationRequest
from app.events import current_owner, emit, mask_phone
from app.ownership import ANONYMOUS
from app.providers import get_provider
from app.providers import mock as mock_provider
from app.providers.base import EvidenceProvider


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class SessionRecord:
    id: str
    # Cleared to "" the moment the session goes terminal (R09). Monitoring is
    # what justified holding it; once monitoring stops there is no question it
    # answers, and an idle process used to hold it until some *other* caller
    # happened to create a session. `masked_phone` outlives it so a client can
    # still recognise which session it is reading.
    phone_number: str
    status: SessionStatus
    created_at: datetime
    expires_at: datetime
    masked_phone: str = ""
    # When the session first became non-ACTIVE. The record is kept this long
    # (`session_terminal_retention_seconds`) so a client that polls can observe
    # the expiry or revocation it was waiting for, and no longer.
    terminal_at: datetime | None = None
    reason: str | None = None
    # sha256 of the API key that opened the session. Reads and deletes filter on
    # it: without it any key could read — and end — any other key's session, and
    # the response carried an unmasked phone number with it (S3).
    owner_hash: str = ANONYMOUS
    task: asyncio.Task | None = field(default=None, repr=False)
    # Terminal events are emitted exactly once even though several paths can
    # notice the same transition — a read, the monitor waking, and the sweeper
    # can all arrive at "this expired" independently.
    emitted: set[str] = field(default_factory=set)
    pending_events: list[str] = field(default_factory=list)

    def is_expired(self, now: datetime) -> bool:
        """Whether the TTL has passed, regardless of what the monitor has done.

        The stored status lags reality by up to one poll interval; the clock
        does not. Everything that decides whether trust still holds asks this,
        never `status` alone (R05).
        """
        return now >= self.expires_at


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
        """Drop terminal records that are past the observation window.

        `_sessions` was never pruned at all; then it was pruned the instant a
        record went terminal, which meant a client polling for the expiry it
        was waiting on could get a 404 instead — the transition it needed to
        see, deleted before it could read it. Records now survive
        `session_terminal_retention_seconds` past the transition and no longer,
        and the raw phone number is gone from them well before that (R09).
        """
        cutoff = _now() - timedelta(seconds=settings.session_terminal_retention_seconds)
        for session_id, rec in list(self._sessions.items()):
            if rec.status == SessionStatus.ACTIVE:
                continue
            if rec.task is not None and not rec.task.done():
                continue
            if rec.terminal_at is None or rec.terminal_at <= cutoff:
                del self._sessions[session_id]

    def _terminal(self, rec: SessionRecord, status: SessionStatus, reason: str) -> bool:
        """Move a session to a terminal status. True only for the call that did it.

        Idempotent because several paths race for the same transition: a read
        after the TTL, the monitor waking from its sleep, and the retention
        sweep can all discover the same expiry. Without this, one expiry could
        emit three `expired` events and overwrite an earlier revocation's
        reason with a later expiry's (R05).
        """
        if rec.status != SessionStatus.ACTIVE:
            return False
        rec.status = status
        rec.reason = reason
        rec.terminal_at = _now()
        # Mock-only stage affordance, but it is module state: see `end`.
        mock_provider.untrip_swap(rec.phone_number)
        return True

    def _expire_if_due(self, rec: SessionRecord) -> bool:
        """Expire on the clock, not on the monitor's schedule.

        The monitor checked its TTL only before sleeping, so a read landing in
        that window was answered ACTIVE by a session whose trust had already
        run out — and with a live provider the sleep is at least 30 seconds
        wide. Any use of a session runs this first (R05).
        """
        if rec.status != SessionStatus.ACTIVE or not rec.is_expired(_now()):
            return False
        self._terminal(rec, SessionStatus.EXPIRED, "TTL reached")
        rec.pending_events.append("expired")
        return True

    def get(self, session_id: str) -> SessionRecord | None:
        """A session the current caller owns, or None.

        None rather than a distinct error, so a session id cannot be probed for
        existence by a key that does not own it.

        Expiry is applied here, so no caller can act on a stale ACTIVE. The
        matching event is queued rather than emitted, because this is the
        synchronous path; `current()` is the async one and flushes it.
        """
        rec = self._sessions.get(session_id)
        if rec is None:
            return None
        if not secrets.compare_digest(rec.owner_hash, current_owner.get() or ANONYMOUS):
            return None
        self._expire_if_due(rec)
        return rec

    async def current(self, session_id: str) -> SessionRecord | None:
        """`get`, plus delivery of any event the expiry check just produced."""
        rec = self.get(session_id)
        if rec is not None:
            await self._flush(rec)
        return rec

    async def _flush(self, rec: SessionRecord) -> None:
        while rec.pending_events:
            await self._emit(rec, rec.pending_events.pop(0))

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
            masked_phone=mask_phone(phone_number),
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
        """End a session the caller owns.

        `get` may already have expired it on the clock. That is not a failure:
        the caller wanted the session stopped and it is stopped, so this
        returns the record with its true terminal status rather than claiming
        an `ended` that did not happen.

        `_terminal` clears the mock's TRIPPED state. That is a stage
        affordance, but it is module state: the session demo reuses Act I's
        number, so retaining it makes the next full run start its clean signup
        with a fabricated SIM swap. Harmless on the live-provider path.
        """
        rec = await self.current(session_id)
        if rec is None:
            return None
        if self._terminal(rec, SessionStatus.ENDED, "ended by caller"):
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
                if await self._expired(rec):
                    return
                # Never sleep past the TTL. A 30-second live-provider poll on a
                # session with 2 seconds left used to spend both calls 28
                # seconds after trust ended; the sleep now lands on the expiry
                # instead, and the check above runs before anything is spent.
                remaining = (rec.expires_at - _now()).total_seconds()
                await asyncio.sleep(max(0.0, min(poll, remaining)))
                if rec.status != SessionStatus.ACTIVE:
                    return
                # Re-checked after waking, and again between the two calls: an
                # expiry that falls between SIM and device must stop the device
                # call, not merely be noticed on the next lap (R05).
                if await self._expired(rec):
                    return
                sim = await provider.gather(Action.SIM_SWAP, req)
                if await self._expired(rec):
                    return
                dev = await provider.gather(Action.DEVICE_SWAP, req)
                flag = next((lk for lk in (sim, dev) if lk.result == Result.FLAG), None)
                if flag is not None:
                    # A signal seen before expiry is still a revocation: the
                    # evidence was gathered while trust was live.
                    if self._terminal(rec, SessionStatus.REVOKED, f"{flag.api}: {flag.detail}"):
                        await self._emit(rec, "revoked")
                    return
        except asyncio.CancelledError:  # pragma: no cover
            return
        except Exception:  # noqa: BLE001 - the monitor must fail closed for every error
            # A monitor that crashes while the session stays ACTIVE creates a
            # false statement of continuing trust. Fail closed and make the
            # conservative revocation visible to the same stream as a signal.
            if self._terminal(rec, SessionStatus.REVOKED, "session monitor failed; trust revoked"):
                await self._emit(rec, "revoked")

    async def _expired(self, rec: SessionRecord) -> bool:
        """Stop here if the TTL has passed. Emits the expiry once."""
        self._expire_if_due(rec)
        await self._flush(rec)
        return rec.status != SessionStatus.ACTIVE

    async def _emit(self, rec: SessionRecord, event: str) -> None:
        if event in rec.emitted:
            return
        rec.emitted.add(event)
        await emit(
            {
                "type": "session",
                "event": event,
                "session_id": rec.id,
                "status": rec.status.value,
                # `emit` masks this itself; passing the raw value keeps that
                # the one place the rule lives, and it is read before the
                # forget below clears it.
                "phone_number": rec.phone_number or rec.masked_phone,
                "reason": rec.reason,
            }
        )
        if rec.status != SessionStatus.ACTIVE:
            self._forget_subject(rec)

    @staticmethod
    def _forget_subject(rec: SessionRecord) -> None:
        """Drop the raw phone number the moment monitoring stops (R09).

        Holding it was justified by the monitor needing to re-ask the operator
        about that number. Once the session is terminal nothing will ask again,
        so the number is retained for no purpose — and it used to be retained
        for the life of an idle process, because the only thing that cleared
        terminal records was some *other* caller creating a session. The masked
        value stays: it identifies the session to its owner without being the
        subject's number.
        """
        rec.phone_number = ""

    def purge_terminal(self) -> int:
        """Sweep terminal records on a timer, not on new-session traffic.

        Called by `app.retention.purge_once`, so one merchant's silence no
        longer leaves another merchant's ended session in memory, and one
        merchant's polling cannot prolong anyone's retention.
        """
        before = len(self._sessions)
        self._prune()
        return before - len(self._sessions)


# Module-level singleton shared by routes, console, and tests.
sessions = SessionManager()
