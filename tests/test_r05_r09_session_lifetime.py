"""R05 and R09 — a session's TTL must bind reads and calls, not just the monitor.

R05: expiry was checked once per lap, immediately *before* sleeping. Everything
that happened during the sleep — reads, and both provider calls on the next lap
— happened on a session whose trust had already run out. With a live provider
the sleep has a 30-second floor, so the window is not theoretical.

R09: a terminal session went on holding the subject's raw phone number, and the
only thing that removed the record was some *other* caller calling `create`. An
idle process therefore kept it indefinitely.

The clock is faked rather than slept through: these are statements about what is
true at a moment in time, and a test that waits for real seconds proves the same
thing more slowly and less exactly.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app import retention
from app.chain.models import EvidenceLink
from app.domain.enums import Action, Result, SessionStatus
from app.events import current_owner
from app.ownership import owner_hash
from app.session import manager as manager_module
from app.session.manager import SessionManager


class Clock:
    """A clock the test moves by hand."""

    def __init__(self) -> None:
        self.now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


class CountingProvider:
    """Records every action it is asked for, and can move the clock while doing it."""

    def __init__(self, clock: Clock | None = None, advance_on: Action | None = None,
                 advance_by: float = 0.0) -> None:
        self.calls: list[Action] = []
        self._clock = clock
        self._advance_on = advance_on
        self._advance_by = advance_by

    async def gather(self, action: Action, request) -> EvidenceLink:
        self.calls.append(action)
        if self._clock and action == self._advance_on:
            self._clock.advance(self._advance_by)
        return EvidenceLink(
            step=1,
            action=action,
            api=action.value,
            result=Result.PASS,
            signal="NO_CHANGE",
            detail="none",
            source="test",
            latency_ms=1,
        )


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(manager_module, "_now", c)
    return c


@pytest.fixture
def owner():
    token = current_owner.set(owner_hash("r05-key"))
    yield
    current_owner.reset(token)


# --- R05 -------------------------------------------------------------------


async def test_read_after_ttl_is_expired_while_the_monitor_sleeps(clock, owner):
    """The acceptance case: read past the TTL, mid-sleep, and get EXPIRED."""
    mgr = SessionManager()
    provider = CountingProvider()
    rec = await mgr.create("+962790000001", ttl_seconds=30, poll_seconds=600, provider=provider)
    assert rec.status == SessionStatus.ACTIVE

    clock.advance(31)
    # The monitor is still inside a 600-second sleep and has not run again.
    read = await mgr.current(rec.id)

    assert read is not None
    assert read.status == SessionStatus.EXPIRED
    assert read.reason == "TTL reached"
    assert provider.calls == []
    await mgr.shutdown()


async def test_no_provider_call_starts_after_the_ttl(clock, owner):
    """A monitor waking past expiry must spend nothing."""
    mgr = SessionManager()
    provider = CountingProvider()
    rec = await mgr.create("+962790000001", ttl_seconds=30, poll_seconds=0.01, provider=provider)

    clock.advance(31)
    await asyncio.sleep(0.05)  # let the monitor wake, notice, and stop

    assert provider.calls == []
    assert rec.status == SessionStatus.EXPIRED
    await mgr.shutdown()


async def test_expiry_between_the_sim_and_device_checks_stops_the_device_call(clock, owner):
    """Expiry landing between the two calls must stop the second one.

    Previously both calls belonged to one lap: once the lap began, the device
    call was going to happen whatever the clock did in between.
    """
    mgr = SessionManager()
    provider = CountingProvider(clock=clock, advance_on=Action.SIM_SWAP, advance_by=31)
    rec = await mgr.create("+962790000001", ttl_seconds=30, poll_seconds=0.01, provider=provider)

    await asyncio.sleep(0.08)

    assert provider.calls == [Action.SIM_SWAP], "the device check ran after the TTL"
    assert rec.status == SessionStatus.EXPIRED
    await mgr.shutdown()


async def test_sleep_is_bounded_by_the_remaining_ttl(clock, owner, monkeypatch):
    """A poll interval longer than the remaining TTL must not be slept through."""
    slept: list[float] = []
    real_sleep = asyncio.sleep

    async def recording_sleep(seconds, *args, **kwargs):
        slept.append(seconds)
        return await real_sleep(0, *args, **kwargs)

    monkeypatch.setattr(manager_module.asyncio, "sleep", recording_sleep)
    mgr = SessionManager()
    provider = CountingProvider()
    await mgr.create("+962790000001", ttl_seconds=5, poll_seconds=600, provider=provider)
    await real_sleep(0.05)

    assert slept, "the monitor never slept"
    assert max(slept) <= 5, f"slept {max(slept)}s past a 5s TTL"
    await mgr.shutdown()


async def test_the_expiry_event_is_emitted_once(clock, owner, monkeypatch):
    """Read, monitor and sweep can each notice the same expiry."""
    events: list[dict] = []

    async def capture(event):
        events.append(event)

    monkeypatch.setattr(manager_module, "emit", capture)
    mgr = SessionManager()
    rec = await mgr.create(
        "+962790000001", ttl_seconds=30, poll_seconds=0.01, provider=CountingProvider()
    )
    clock.advance(31)

    await mgr.current(rec.id)          # a read notices
    await asyncio.sleep(0.05)          # the monitor wakes and notices
    await mgr.current(rec.id)          # another read notices

    expired = [e for e in events if e.get("event") == "expired"]
    assert len(expired) == 1, f"expected one expiry event, got {len(expired)}"
    await mgr.shutdown()


async def test_ending_an_already_expired_session_reports_the_true_status(clock, owner):
    """`end` must not overwrite an expiry with a claim it was ended by a caller."""
    mgr = SessionManager()
    rec = await mgr.create(
        "+962790000001", ttl_seconds=30, poll_seconds=600, provider=CountingProvider()
    )
    clock.advance(31)

    ended = await mgr.end(rec.id)

    assert ended is not None
    assert ended.status == SessionStatus.EXPIRED
    assert ended.reason == "TTL reached"
    await mgr.shutdown()


# --- R09 -------------------------------------------------------------------


async def test_terminal_transition_clears_the_raw_phone_number(clock, owner):
    mgr = SessionManager()
    rec = await mgr.create(
        "+962790000001", ttl_seconds=30, poll_seconds=600, provider=CountingProvider()
    )
    assert rec.phone_number == "+962790000001"

    await mgr.end(rec.id)

    assert rec.phone_number == "", "a terminal session still holds the subject's number"
    assert rec.masked_phone == "+96…01", "the masked value must survive for the owner"
    await mgr.shutdown()


async def test_expiry_clears_the_raw_phone_number_too(clock, owner):
    mgr = SessionManager()
    rec = await mgr.create(
        "+962790000001", ttl_seconds=30, poll_seconds=0.01, provider=CountingProvider()
    )
    clock.advance(31)
    await asyncio.sleep(0.05)

    assert rec.status == SessionStatus.EXPIRED
    assert rec.phone_number == ""
    await mgr.shutdown()


async def test_a_terminal_record_stays_readable_for_its_window_then_goes(clock, owner):
    """The client polling for the expiry must be able to see it."""
    mgr = SessionManager()
    rec = await mgr.create(
        "+962790000001", ttl_seconds=30, poll_seconds=600, provider=CountingProvider()
    )
    await mgr.end(rec.id)
    await asyncio.sleep(0.01)

    clock.advance(10)
    mgr.purge_terminal()
    assert await mgr.current(rec.id) is not None, "the terminal status was deleted before it could be read"

    clock.advance(200)
    assert mgr.purge_terminal() == 1
    assert await mgr.current(rec.id) is None
    await mgr.shutdown()


async def test_idle_cleanup_reclaims_without_new_session_traffic(clock, owner, monkeypatch):
    """`_prune` used to run only inside `create`, so an idle process kept everything."""
    mgr = SessionManager()
    monkeypatch.setattr(retention, "sessions", mgr)
    rec = await mgr.create(
        "+962790000001", ttl_seconds=30, poll_seconds=600, provider=CountingProvider()
    )
    await mgr.end(rec.id)
    await asyncio.sleep(0.01)
    clock.advance(200)

    deleted = retention.purge_once()

    assert deleted["terminal_sessions"] == 1
    assert mgr._sessions == {}
    await mgr.shutdown()


async def test_one_owners_polling_cannot_prolong_anothers_retention(clock, monkeypatch):
    """Retention is per-record and on a clock, not a side effect of anyone's traffic."""
    mgr = SessionManager()
    monkeypatch.setattr(retention, "sessions", mgr)

    first = current_owner.set(owner_hash("merchant-a"))
    a = await mgr.create("+962790000001", ttl_seconds=30, poll_seconds=600,
                         provider=CountingProvider())
    await mgr.end(a.id)
    current_owner.reset(first)

    second = current_owner.set(owner_hash("merchant-b"))
    b = await mgr.create("+962790000002", ttl_seconds=30, poll_seconds=600,
                         provider=CountingProvider())
    await asyncio.sleep(0.01)
    clock.advance(200)

    # Merchant B is still polling its own live session.
    assert await mgr.current(b.id) is not None
    retention.purge_once()
    current_owner.reset(second)

    first = current_owner.set(owner_hash("merchant-a"))
    assert await mgr.current(a.id) is None, "merchant B's traffic kept merchant A's record alive"
    current_owner.reset(first)
    await mgr.shutdown()
