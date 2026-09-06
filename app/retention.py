"""Deleting what no longer answers a question.

Two tables here record who was in contact with whom. `screen_events` exists to
answer one question about the recent past — how many different people has this
number reached in the last ten minutes — and `call_announcements` records an
institution telling this service who it is about to ring. Neither is useful
outside its window, and both keep growing after it: that is a retention
problem, not a disk-space one, and it is named in `ScreenEventRow`'s own
docstring.

Both purge functions existed and neither had a caller anywhere in the app, so
in practice nothing was ever deleted. This is the caller.
"""

from __future__ import annotations

import asyncio
import logging

from app import announce, velocity
from app.config import settings
from app.db import challenges, outcomes, proof_shares

log = logging.getLogger("isnad")


def purge_once() -> dict[str, int]:
    """One sweep of everything past its window. Returns what it deleted."""
    return {
        "announcements": announce.purge_expired(),
        "screen_events": velocity.purge_older_than(velocity.retention_seconds()),
        "challenge_followups": challenges.purge_followups(),
        "idempotency_records": challenges.purge_idempotency_records(),
        "outcome_events": outcomes.purge_outcomes(),
        "proof_shares": proof_shares.purge_expired_shares(),
    }


async def purge_once_async() -> dict[str, int]:
    # SQLite writes block the event loop — same reasoning as store.py.
    return await asyncio.to_thread(purge_once)


async def run_forever(interval_seconds: int) -> None:
    """Sweep on a timer until cancelled.

    A failed sweep must not end the loop. A transient database error would
    otherwise stop retention permanently and silently, and nothing else in the
    process is watching — the tables would simply resume growing forever, which
    is exactly the state this exists to leave behind.
    """
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            deleted = await purge_once_async()
            if any(deleted.values()):
                log.info("retention sweep deleted %s", deleted)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("retention sweep failed; continuing")


def start() -> asyncio.Task | None:
    """Start the sweeper, or None when it is disabled (interval <= 0)."""
    interval = int(settings.purge_interval_seconds)
    if interval <= 0:
        return None
    return asyncio.create_task(run_forever(interval), name="isnad-retention")
