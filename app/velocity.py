from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.chain.subject import subject_hash
from app.config import settings
from app.db.database import SessionLocal
from app.db.models import ScreenEventRow
from app.events import current_owner
from app.ownership import ANONYMOUS
from app.policy.engine import PolicyEngine


def _owner() -> str:
    """The tenant this request belongs to, set at the auth boundary (S2)."""
    return current_owner.get() or ANONYMOUS


def record(caller_number: str, callee_number: str) -> None:
    """Note that this caller was screened against this callee, for this tenant."""
    with SessionLocal() as session:
        session.add(
            ScreenEventRow(
                id="scr_" + uuid.uuid4().hex[:20],
                caller_hash=subject_hash(caller_number),
                callee_hash=subject_hash(callee_number),
                owner_hash=_owner(),
                at=datetime.now(UTC),
            )
        )
        session.commit()


def distinct_callees(caller_number: str, window_seconds: int) -> int:
    """How many different people this number has been screened against lately.

    DISTINCT matters more than COUNT: one worried customer checking the same
    number twenty times is not a campaign, and counting rows would call it one.

    SCOPED TO THE CALLING TENANT. Counting across every tenant is the version
    with the network effect — one merchant's sighting warning all the others —
    and it is also trivially poisonable: any key holder could send thirty
    screens with invented callees and mark any bank's switchboard as a spoof for
    everybody. A cross-tenant count needs an owner-diversity threshold and a
    trust model between tenants, which this does not have yet. Per-tenant is the
    honest version to ship, and it is what to say on stage.
    """
    since = datetime.now(UTC) - timedelta(seconds=window_seconds)
    with SessionLocal() as session:
        return int(
            session.execute(
                select(func.count(func.distinct(ScreenEventRow.callee_hash))).where(
                    ScreenEventRow.caller_hash == subject_hash(caller_number),
                    ScreenEventRow.owner_hash == _owner(),
                    ScreenEventRow.at > since,
                )
            ).scalar_one()
        )


def is_high_velocity(engine: PolicyEngine, caller_number: str) -> tuple[bool, int, int]:
    """(over_threshold, observed, threshold). Threshold 0 disables the check."""
    window, threshold = engine.velocity_window(), engine.velocity_threshold()
    if threshold <= 0:
        return False, 0, threshold
    observed = distinct_callees(caller_number, window)
    return observed >= threshold, observed, threshold


def purge_older_than(seconds: int) -> int:
    """Drop events outside any window anyone will ask about.

    This table exists to answer one question about the recent past, so keeping
    it forever would accumulate a record of who was screened against whom for no
    benefit — a retention question, not a disk-space one.
    """
    cutoff = datetime.now(UTC) - timedelta(seconds=seconds)
    with SessionLocal() as session:
        deleted = session.query(ScreenEventRow).filter(ScreenEventRow.at <= cutoff).delete()
        session.commit()
    return deleted


async def record_async(caller_number: str, callee_number: str) -> None:
    await asyncio.to_thread(record, caller_number, callee_number)


async def is_high_velocity_async(engine: PolicyEngine, caller_number: str) -> tuple[bool, int, int]:
    return await asyncio.to_thread(is_high_velocity, engine, caller_number)


def retention_seconds() -> int:
    return int(settings.velocity_retention_seconds)
