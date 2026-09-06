"""Durable event journal for one investigation run (I14).

`persist_event()` is called from `app.events.emit()` before fan-out, and
only for events that already carry a `run_id` — the console/investigator's
existing convention for a run a client might want to replay. Sequence
numbers are assigned by the database's own unique constraint racing two
concurrent writers, the same IntegrityError-as-race-resolution pattern
`announce.find` and P3's challenge attempts already use, not a Python-level
counter that could double-assign under concurrency.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import RunEventRow

# Structured fields safe to persist. Never a raw phone number, prompt, token
# or unrestricted provider/exception string (I1's own diagnostic-code rule
# applies here too).
_ALLOWED_BODY_KEYS = frozenset(
    {
        "chain_id",
        "hypothesis",
        "prior_p_fraud",
        "phase",
        "action",
        "api",
        "rationale",
        "planner",
        "cost",
        "score",
        "budget_left",
        "step",
        "result",
        "signal",
        "source",
        "max_age_hours",
        "p_fraud",
        "decision",
        "chain_grade",
        "confidence",
        "evidence_steps",
        "evidence_cost",
        "latency_ms",
    }
)


def _allowlisted_body(event: dict) -> dict:
    return {k: v for k, v in event.items() if k in _ALLOWED_BODY_KEYS}


def _now() -> datetime:
    return datetime.now(UTC)


def persist_event(owner: str, run_id: str, event: dict) -> int | None:
    """Returns the assigned sequence number, or None if persistence failed —
    the caller must not claim durable replay is available for this event
    when that happens; it does not abort the live fan-out either way."""
    if not run_id:
        return None
    body = _allowlisted_body(event)
    event_type = event.get("type", "unknown")

    # A bounded retry, not an unlimited one: two concurrent emits for the
    # same run racing to claim the next sequence is expected and should
    # usually resolve on the next attempt: only a genuinely persistent
    # failure (or unlucky repeated contention) gives up and drops the event
    # rather than blocking the live investigation indefinitely.
    for _attempt in range(3):
        with SessionLocal() as session:
            current_max = (
                session.query(func.max(RunEventRow.sequence))
                .filter(RunEventRow.owner_hash == owner, RunEventRow.run_id == run_id)
                .scalar()
            )
            next_sequence = (current_max or 0) + 1
            session.add(
                RunEventRow(
                    owner_hash=owner,
                    run_id=run_id,
                    sequence=next_sequence,
                    event_type=event_type,
                    body_json=json.dumps(body),
                    server_time=_now(),
                )
            )
            try:
                session.commit()
            except IntegrityError:
                # A concurrent emit for the same run claimed this sequence
                # first. Retry with a freshly read max rather than giving up
                # immediately.
                session.rollback()
                continue
            return next_sequence
    return None


def events_after(owner: str, run_id: str, *, after: int) -> list[dict]:
    """Persisted events for this owner's run, strictly newer than `after`,
    in order. Bounded page size — a replay client asking for everything at
    once still gets a finite response."""
    if not run_id:
        return []
    with SessionLocal() as session:
        rows = (
            session.query(RunEventRow)
            .filter(
                RunEventRow.owner_hash == owner,
                RunEventRow.run_id == run_id,
                RunEventRow.sequence > after,
            )
            .order_by(RunEventRow.sequence.asc())
            .limit(settings.run_replay_page_size)
            .all()
        )
        return [
            {
                "sequence": row.sequence,
                "event_type": row.event_type,
                "body": json.loads(row.body_json),
                "server_time": row.server_time.isoformat(),
            }
            for row in rows
        ]


def has_gap(owner: str, run_id: str, *, after: int) -> bool:
    """True when a client's own cursor cannot be trusted: it claims to have
    already seen `after` events for a run that either never persisted that
    many (retention already dropped them, or they were never durable) or
    does not exist for this owner at all. `after == 0` is always gap-free —
    starting fresh needs no prior event to confirm."""
    if after <= 0:
        return False
    with SessionLocal() as session:
        exists = (
            session.query(RunEventRow)
            .filter(RunEventRow.owner_hash == owner, RunEventRow.run_id == run_id, RunEventRow.sequence == after)
            .first()
        )
        return exists is None


def purge_older_than(retention_seconds: int) -> int:
    from datetime import timedelta

    cutoff = _now() - timedelta(seconds=retention_seconds)
    with SessionLocal() as session:
        deleted = (
            session.query(RunEventRow).filter(RunEventRow.server_time <= cutoff).delete(synchronize_session=False)
        )
        session.commit()
    return deleted
