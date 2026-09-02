"""Trust-with-a-TTL: live session revocation."""

from __future__ import annotations

import asyncio

import pytest

from app.domain.enums import SessionStatus
from app.providers import mock as mock_provider
from app.providers.mock import MockProvider
from app.session.manager import SessionManager


@pytest.fixture(autouse=True)
def _clean_trips():
    mock_provider.TRIPPED.clear()
    yield
    mock_provider.TRIPPED.clear()


@pytest.mark.asyncio
async def test_session_starts_active():
    mgr = SessionManager()
    rec = await mgr.create(
        "+962790000001", ttl_seconds=30, poll_seconds=0.05, provider=MockProvider()
    )
    assert rec.status == SessionStatus.ACTIVE
    await mgr.end(rec.id)


@pytest.mark.asyncio
async def test_mid_session_swap_revokes_live():
    """Start a clean session, inject a SIM swap, monitor must revoke it."""
    mgr = SessionManager()
    rec = await mgr.create(
        "+962790000001", ttl_seconds=30, poll_seconds=0.05, provider=MockProvider()
    )
    assert rec.status == SessionStatus.ACTIVE

    mock_provider.trip_swap("+962790000001")  # the on-stage SIM swap

    for _ in range(40):  # up to ~2s
        if rec.status == SessionStatus.REVOKED:
            break
        await asyncio.sleep(0.05)

    assert rec.status == SessionStatus.REVOKED
    assert "swap" in (rec.reason or "").lower()
    # The stage demo uses this number for Act I on its next run. Leaving the
    # module-global mock trip behind makes that otherwise clean signup start
    # with a fabricated SIM swap on the second demo run.
    assert rec.phone_number not in mock_provider.TRIPPED


@pytest.mark.asyncio
async def test_manual_end():
    mgr = SessionManager()
    rec = await mgr.create(
        "+962790000001", ttl_seconds=30, poll_seconds=0.05, provider=MockProvider()
    )
    mock_provider.trip_swap(rec.phone_number)
    ended = await mgr.end(rec.id)
    assert ended is not None and ended.status == SessionStatus.ENDED
    assert rec.phone_number not in mock_provider.TRIPPED


@pytest.mark.asyncio
async def test_ttl_expiry():
    mgr = SessionManager()
    rec = await mgr.create(
        "+962790000001", ttl_seconds=0, poll_seconds=0.02, provider=MockProvider()
    )
    for _ in range(30):
        if rec.status == SessionStatus.EXPIRED:
            break
        await asyncio.sleep(0.02)
    assert rec.status == SessionStatus.EXPIRED


@pytest.mark.asyncio
async def test_monitor_failure_revokes_trust_instead_of_leaving_it_active():
    class FailingProvider:
        async def gather(self, action, request):
            raise RuntimeError("provider connection lost")

    mgr = SessionManager()
    rec = await mgr.create(
        "+962790000001", ttl_seconds=30, poll_seconds=0.01, provider=FailingProvider()
    )
    for _ in range(30):
        if rec.status == SessionStatus.REVOKED:
            break
        await asyncio.sleep(0.01)

    assert rec.status == SessionStatus.REVOKED
    assert rec.reason == "session monitor failed; trust revoked"
