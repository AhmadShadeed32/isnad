"""Caller velocity — the signal no per-call check can produce.

Every other check here judges one call in isolation. A campaign is not one call:
it is one number reaching hundreds of people in minutes, and that shape is
invisible to any single-call check however good it is.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import velocity
from app.config import settings
from app.main import app
from app.policy.engine import get_engine

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}
CALLER = "+96265000000"  # Demo Bank's real switchboard number


@pytest.fixture(autouse=True)
def _clean():
    from app.db.database import SessionLocal
    from app.db.models import CallAnnouncementRow, ScreenEventRow

    with SessionLocal() as session:
        session.query(ScreenEventRow).delete()
        session.query(CallAnnouncementRow).delete()
        session.commit()
    yield


def _engine():
    return get_engine(str(settings.policy_path))


def _as(owner: str):
    """Read the counters as a given tenant.

    The counts are per-owner, so a direct call from a test has to say which
    tenant it is asking as — exactly like a request does at the auth boundary.
    """
    from app.events import current_owner

    current_owner.set(owner)


def _owner_of(key: str) -> str:
    from app.api.deps import owner_for

    return owner_for(key)


def _screen(caller=CALLER, callee="+962790000001"):
    return client.post(
        "/v1/screen",
        json={"caller_number": caller, "callee_number": callee},
        headers=AUTH,
    ).json()


def _burst(n, caller=CALLER):
    for index in range(n):
        _screen(caller, f"+96279{index:06d}")


# ---- the counting ----


def test_distinct_callees_counts_people_not_calls():
    """One worried customer checking the same number twenty times is not a
    campaign, and counting rows would call it one."""
    for _ in range(20):
        _screen(callee="+962790000001")
    _as(_owner_of("demo-merchant-key"))
    assert velocity.distinct_callees(CALLER, 600) == 1


def test_distinct_callees_counts_each_new_person():
    _burst(5)
    _as(_owner_of("demo-merchant-key"))
    assert velocity.distinct_callees(CALLER, 600) == 5


def test_events_outside_the_window_do_not_count():
    import datetime as dt

    from app.db.database import SessionLocal
    from app.db.models import ScreenEventRow

    _burst(5)
    with SessionLocal() as session:
        for row in session.query(ScreenEventRow).all():
            row.at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=3600)
        session.commit()
    _as(_owner_of("demo-merchant-key"))
    assert velocity.distinct_callees(CALLER, 600) == 0


def test_the_callee_is_never_stored_as_a_number():
    """Counting DISTINCT callees needs to tell two people apart. It does not
    need to know who either of them is."""
    from app.db.database import SessionLocal
    from app.db.models import ScreenEventRow

    _screen(callee="+962790000001")
    with SessionLocal() as session:
        rows = session.query(ScreenEventRow).all()
    assert rows
    assert all("+962790000001" not in row.callee_hash for row in rows)
    assert all(len(row.callee_hash) == 64 for row in rows)


def test_velocity_is_per_caller():
    _burst(30)
    _as(_owner_of("demo-merchant-key"))
    assert velocity.distinct_callees("+96280022222", 600) == 0


# ---- the label ----


def test_a_burst_flags_the_caller():
    _burst(_engine().velocity_threshold() + 2)
    body = _screen(callee="+962790009999")
    assert body["label"] == "SUSPECTED_SPOOF"
    assert body["basis"] == "caller_velocity"


def test_a_quiet_number_is_not_flagged():
    body = _screen()
    assert body["basis"] == "registry_match_unannounced"


def test_velocity_outranks_a_reassuring_registry_hit():
    """A spoofed campaign wearing a real institution's number would otherwise
    land on the "belongs to Demo Bank" branch and read as reassuring."""
    _burst(_engine().velocity_threshold() + 2)
    body = _screen(callee="+962790009999")
    assert body["basis"] == "caller_velocity"
    assert body["institution_name"] == "Demo Bank"  # it IS the bank's number


def test_an_announcement_still_wins():
    """An institution that told us it was calling, and proved who it was, is
    allowed to call a lot of people."""
    from app import announce

    _burst(_engine().velocity_threshold() + 2)
    announce.record(
        institution_id="demo-bank-jo",
        api_key="demo-merchant-key",
        calling_participant=CALLER,
        called_participant="+962790000001",
        display_name="Demo Bank",
    )
    body = _screen(callee="+962790000001")
    assert body["label"] == "VERIFIED_INSTITUTION"


def test_the_check_can_be_disabled(monkeypatch):
    engine = _engine()
    monkeypatch.setitem(engine.cfg["velocity"], "distinct_callees_flag", 0)
    _burst(30)
    _as(_owner_of("demo-merchant-key"))
    assert velocity.is_high_velocity(engine, CALLER)[0] is False


# ---- Tier 2 ----


@pytest.mark.asyncio
async def test_velocity_reaches_the_signed_chain():
    from app.api.routes_reverse import run_reverse
    from app.providers.mock import MockProvider

    _burst(_engine().velocity_threshold() + 2)
    _as(_owner_of("demo-merchant-key"))
    verdict = await run_reverse(CALLER, MockProvider(), claimed_identity="Demo Bank")
    assert "CALLER_HIGH_VELOCITY" in [link.signal for link in verdict.chain]


@pytest.mark.asyncio
async def test_tier_two_records_the_calls_it_screens():
    """A campaign run entirely through /v1/reverse-verify used to be invisible.

    Only the Tier 1 screen wrote rows, so the counter never saw a caller who
    reached everybody through Tier 2 — and CALLER_HIGH_VELOCITY, the one signal
    here that no per-call check can produce, never fired for them.
    """
    from app.api.routes_reverse import run_reverse
    from app.providers.mock import MockProvider

    _as(_owner_of("demo-merchant-key"))
    threshold = _engine().velocity_threshold()
    for index in range(threshold + 2):
        await run_reverse(
            CALLER,
            MockProvider(),
            callee_number=f"+96279{index:06d}",
        )
    assert velocity.distinct_callees(CALLER, 600) >= threshold

    verdict = await run_reverse(
        CALLER,
        MockProvider(),
        callee_number="+962790009999",
    )
    assert "CALLER_HIGH_VELOCITY" in [link.signal for link in verdict.chain]


@pytest.mark.asyncio
async def test_tier_two_records_nothing_without_a_callee():
    """ "How many different people has this number reached" cannot be asked
    without knowing who was reached. A reverse check with no callee still runs;
    it just contributes nothing to a count it has no term for."""
    from app.api.routes_reverse import run_reverse
    from app.providers.mock import MockProvider

    _as(_owner_of("demo-merchant-key"))
    await run_reverse(CALLER, MockProvider())
    assert velocity.distinct_callees(CALLER, 600) == 0


# ---- retention ----


def test_events_are_purgeable():
    """The table answers one question about the recent past. Kept forever it
    would accumulate a record of who was screened against whom."""
    import datetime as dt

    from app.db.database import SessionLocal
    from app.db.models import ScreenEventRow

    _burst(3)
    with SessionLocal() as session:
        for row in session.query(ScreenEventRow).all():
            row.at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=7200)
        session.commit()
    assert velocity.purge_older_than(3600) == 3
    assert velocity.distinct_callees(CALLER, 600) == 0


# ---- tenant isolation (security audit, 31 Aug) ----


def test_one_tenant_cannot_poison_another_tenants_velocity():
    """The finding that made this per-owner.

    Counting across every tenant let any key holder send ~30 screens with
    invented callees and mark any bank's switchboard as a spoof for EVERYBODY
    for the length of the window — and nothing recorded who did it.
    """
    _burst(_engine().velocity_threshold() + 5)  # attacker's traffic

    _as(_owner_of("another-tenant"))
    assert velocity.distinct_callees(CALLER, 600) == 0
    assert velocity.is_high_velocity(_engine(), CALLER)[0] is False


def test_every_screen_event_records_who_observed_it():
    """Without attribution the poisoning above is invisible after the fact."""
    from app.db.database import SessionLocal
    from app.db.models import ScreenEventRow

    _screen()
    with SessionLocal() as session:
        rows = session.query(ScreenEventRow).all()
    assert rows and all(row.owner_hash for row in rows)
