"""Retention — the sweeper that finally has a caller.

`announce.purge_expired()` and `velocity.purge_older_than()` both existed and
neither was called from anywhere in the app, so in practice nothing was ever
deleted. Two tables that record who was in contact with whom grew forever,
which is the retention problem `ScreenEventRow`'s own docstring names.
"""

from __future__ import annotations

import asyncio
import datetime as dt

import pytest

from app import announce, retention, velocity
from app.config import settings
from app.db.database import SessionLocal
from app.db.models import AnnouncementUseRow, CallAnnouncementRow, ScreenEventRow

CALLER = "+96265000000"
CALLEE = "+962790000001"


@pytest.fixture(autouse=True)
def _clean():
    from app.db.database import init_db

    init_db()  # the suite shares one in-memory database
    with SessionLocal() as session:
        session.query(AnnouncementUseRow).delete()
        session.query(CallAnnouncementRow).delete()
        session.query(ScreenEventRow).delete()
        session.commit()
    yield


def _age_announcements(seconds: int) -> None:
    with SessionLocal() as session:
        for row in session.query(CallAnnouncementRow).all():
            row.expires_at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=seconds)
        session.commit()


def _counts() -> tuple[int, int, int]:
    with SessionLocal() as session:
        return (
            session.query(CallAnnouncementRow).count(),
            session.query(AnnouncementUseRow).count(),
            session.query(ScreenEventRow).count(),
        )


def test_one_sweep_clears_both_tables():
    announce.record(
        institution_id="demo-bank-jo",
        api_key="demo-merchant-key",
        calling_participant=CALLER,
        called_participant=CALLEE,
        display_name="Demo Bank",
    )
    velocity.record(CALLER, CALLEE)
    _age_announcements(60)
    with SessionLocal() as session:
        for row in session.query(ScreenEventRow).all():
            row.at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=7200)
        session.commit()

    deleted = retention.purge_once()
    assert deleted["announcements"] == 1
    assert deleted["screen_events"] == 1
    assert _counts() == (0, 0, 0)


def test_the_use_rows_go_with_the_announcement_they_belonged_to():
    """`announcement_uses` has no foreign key, so deleting the announcements
    alone left a row per reader per expired announcement behind forever — the
    same unbounded growth, in the table added this morning to fix the burn
    attack."""
    announce.record(
        institution_id="demo-bank-jo",
        api_key="demo-merchant-key",
        calling_participant=CALLER,
        called_participant=CALLEE,
        display_name="Demo Bank",
    )
    assert announce.find(CALLER, CALLEE, consume=True) is not None
    assert _counts()[1] == 1, "the read should have recorded a use"

    _age_announcements(60)
    retention.purge_once()
    assert _counts()[:2] == (0, 0)


def test_a_live_announcement_survives_the_sweep():
    """Expiry is enforced on read; the sweep must not shorten the window."""
    announce.record(
        institution_id="demo-bank-jo",
        api_key="demo-merchant-key",
        calling_participant=CALLER,
        called_participant=CALLEE,
        display_name="Demo Bank",
    )
    assert retention.purge_once()["announcements"] == 0
    # Consuming, because a non-consuming read only answers for a reader who has
    # already spent their use — one announcement, one verification, to one
    # party, once.
    assert announce.find(CALLER, CALLEE, consume=True) is not None


@pytest.mark.asyncio
async def test_the_sweeper_survives_a_failed_sweep(monkeypatch):
    """A transient database error must not end the loop. Nothing else in the
    process is watching, so a loop that dies leaves the tables growing forever
    and says nothing."""
    calls = {"n": 0}

    async def boom() -> dict:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("database is locked")
        return {"announcements": 0, "screen_events": 0}

    monkeypatch.setattr(retention, "purge_once_async", boom)
    monkeypatch.setattr(settings, "purge_interval_seconds", 0.01, raising=False)

    task = asyncio.create_task(retention.run_forever(0.01))
    for _ in range(200):
        await asyncio.sleep(0.01)
        if calls["n"] >= 2:
            break
    task.cancel()
    assert calls["n"] >= 2, "the loop stopped after the first failure"


def test_the_sweeper_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(settings, "purge_interval_seconds", 0, raising=False)
    assert retention.start() is None


def test_the_app_sweeps_at_boot_and_starts_the_sweeper(monkeypatch):
    """The whole point of this file: the purges have a caller now.

    The boot sweep matters on its own — a process that restarts more often than
    the interval would otherwise never sweep at all.
    """
    from fastapi.testclient import TestClient

    from app import main
    from app.main import app

    swept, started, cancelled = [], [], []

    async def spy_sweep() -> dict:
        swept.append(True)
        return {"announcements": 0, "screen_events": 0}

    class _Task:
        def cancel(self) -> None:
            cancelled.append(True)

    def spy_start():
        started.append(True)
        return _Task()

    monkeypatch.setattr(main.retention, "purge_once_async", spy_sweep)
    monkeypatch.setattr(main.retention, "start", spy_start)

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert swept and started

    assert cancelled, "the sweeper must be cancelled on shutdown"
