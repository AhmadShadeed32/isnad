"""CHALLENGE followups: what a merchant did after a signed CHALLENGE decision.

Never touches `ChainRow` (P3's own rule). A followup attempt and its reported
result live in their own append-mostly tables and are read back separately
from the signed chain — see `store.py` for the thing this must never rewrite.
"""

from __future__ import annotations

import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import ChallengeAttemptRow, ChallengeEventRow, IdempotencyRecordRow
from app.events import current_owner
from app.ownership import ANONYMOUS

REPORTABLE_RESULTS = ("PASSED", "FAILED", "ABANDONED")
_TERMINAL = {"PASSED", "FAILED", "ABANDONED", "EXPIRED"}


class AttemptNotFound(RuntimeError):
    """No such attempt for this chain, scoped to the caller (404, never 409:
    same reasoning as store._owned — existence must not be probeable)."""


class AttemptNotPending(RuntimeError):
    """The attempt already has a terminal result, from a prior report or from
    expiry, and this report conflicts with it."""

    def __init__(self, status: str) -> None:
        super().__init__(status)
        self.status = status


class IdempotencyKeyConflict(RuntimeError):
    """The Idempotency-Key was already used for a different target or body."""


@dataclass
class WriteOutcome:
    response: dict
    status_code: int
    replayed: bool


def _owner() -> str:
    """The tenant this request belongs to — same ContextVar store.py reads."""
    return current_owner.get() or ANONYMOUS


def _now() -> datetime:
    return datetime.now(UTC)


def _reserve_idempotency(
    session, operation: str, idempotency_key: str, fingerprint: str
) -> IdempotencyRecordRow | None:
    """The prior record for this (owner, operation, key), after checking it
    still matches this request. None means: no prior write, safe to proceed."""
    existing = session.get(IdempotencyRecordRow, (_owner(), operation, idempotency_key))
    if existing is None:
        return None
    if not hmac.compare_digest(existing.request_fingerprint, fingerprint):
        raise IdempotencyKeyConflict(idempotency_key)
    return existing


def _finalize_or_replay(
    session, operation: str, idempotency_key: str, fingerprint: str, response: dict, status_code: int
) -> WriteOutcome:
    """Commit `response` under this idempotency key, or — if a concurrent
    request won the same key first — replay what it wrote instead.

    The insert-then-catch-IntegrityError pattern is `announce.find`'s (P4a
    precedent): the primary key is the actual race resolution, not this
    Python-level check-then-write, which only saves the common case a round
    trip.
    """
    session.add(
        IdempotencyRecordRow(
            owner_hash=_owner(),
            operation=operation,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            response_json=json.dumps(response),
            status_code=status_code,
            created_at=_now(),
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.get(IdempotencyRecordRow, (_owner(), operation, idempotency_key))
        if existing is None:
            raise
        if not hmac.compare_digest(existing.request_fingerprint, fingerprint):
            raise IdempotencyKeyConflict(idempotency_key) from None
        return WriteOutcome(json.loads(existing.response_json), existing.status_code, replayed=True)
    return WriteOutcome(response, status_code, replayed=False)


def _expire_if_due(session, attempt: ChallengeAttemptRow, now: datetime) -> bool:
    """CAS PENDING -> EXPIRED if the attempt's window has passed.

    A plain `UPDATE ... WHERE status='PENDING'` with a rowcount check, not a
    read-then-write: two callers racing this (the sweeper and a merchant's own
    report) must not both believe they made the transition.
    """
    if attempt.status != "PENDING" or now <= attempt.expires_at:
        return False
    updated = (
        session.query(ChallengeAttemptRow)
        .filter(ChallengeAttemptRow.attempt_id == attempt.attempt_id, ChallengeAttemptRow.status == "PENDING")
        .update({"status": "EXPIRED", "terminal_at": now}, synchronize_session=False)
    )
    if updated:
        attempt.status = "EXPIRED"
        attempt.terminal_at = now
    return bool(updated)


def create_attempt(
    *, chain_id: str, method: str, idempotency_key: str, fingerprint: str
) -> WriteOutcome:
    operation = "challenge.create"
    with SessionLocal() as session:
        existing = _reserve_idempotency(session, operation, idempotency_key, fingerprint)
        if existing is not None:
            return WriteOutcome(json.loads(existing.response_json), existing.status_code, replayed=True)

        now = _now()
        attempt = ChallengeAttemptRow(
            attempt_id="chgat_" + uuid.uuid4().hex[:20],
            chain_id=chain_id,
            owner_hash=_owner(),
            method=method,
            status="PENDING",
            created_at=now,
            expires_at=now + timedelta(seconds=settings.challenge_attempt_ttl_seconds),
        )
        session.add(attempt)
        response = {
            "attempt_id": attempt.attempt_id,
            "chain_id": chain_id,
            "method": method,
            "status": "PENDING",
            "created_at": attempt.created_at.isoformat(),
            "expires_at": attempt.expires_at.isoformat(),
        }
        return _finalize_or_replay(session, operation, idempotency_key, fingerprint, response, 201)


def report_event(
    *, chain_id: str, attempt_id: str, result: str, idempotency_key: str, fingerprint: str
) -> WriteOutcome:
    operation = "challenge.event"
    with SessionLocal() as session:
        existing = _reserve_idempotency(session, operation, idempotency_key, fingerprint)
        if existing is not None:
            return WriteOutcome(json.loads(existing.response_json), existing.status_code, replayed=True)

        owner = _owner()
        attempt = session.get(ChallengeAttemptRow, attempt_id)
        if attempt is None or attempt.chain_id != chain_id or not hmac.compare_digest(attempt.owner_hash, owner):
            raise AttemptNotFound(attempt_id)

        now = _now()
        if _expire_if_due(session, attempt, now):
            # Persist the expiry regardless of what happens next: it is a real
            # server-side fact, not contingent on this report succeeding.
            session.commit()
        if attempt.status != "PENDING":
            raise AttemptNotPending(attempt.status)

        updated = (
            session.query(ChallengeAttemptRow)
            .filter(ChallengeAttemptRow.attempt_id == attempt_id, ChallengeAttemptRow.status == "PENDING")
            .update({"status": result, "terminal_at": now}, synchronize_session=False)
        )
        if not updated:
            # Lost a race against a concurrent report or the sweeper between
            # the check above and this update.
            session.rollback()
            raise AttemptNotPending("terminal")

        session.add(
            ChallengeEventRow(
                event_id="chgev_" + uuid.uuid4().hex[:20],
                attempt_id=attempt_id,
                result=result,
                provenance="merchant_reported",
                reported_at=now,
            )
        )
        response = {"attempt_id": attempt_id, "status": result, "result": result, "reported_at": now.isoformat()}
        return _finalize_or_replay(session, operation, idempotency_key, fingerprint, response, 200)


def timeline(*, chain_id: str) -> list[dict]:
    owner = _owner()
    now = _now()
    with SessionLocal() as session:
        attempts = (
            session.query(ChallengeAttemptRow)
            .filter(ChallengeAttemptRow.chain_id == chain_id, ChallengeAttemptRow.owner_hash == owner)
            .order_by(ChallengeAttemptRow.created_at.asc())
            .all()
        )
        changed = False
        result: list[dict] = []
        for attempt in attempts:
            if _expire_if_due(session, attempt, now):
                changed = True
            events = (
                session.query(ChallengeEventRow)
                .filter(ChallengeEventRow.attempt_id == attempt.attempt_id)
                .order_by(ChallengeEventRow.reported_at.asc())
                .all()
            )
            result.append(
                {
                    "attempt_id": attempt.attempt_id,
                    "method": attempt.method,
                    "status": attempt.status,
                    "created_at": attempt.created_at.isoformat(),
                    "expires_at": attempt.expires_at.isoformat(),
                    "events": [
                        {"result": e.result, "provenance": e.provenance, "reported_at": e.reported_at.isoformat()}
                        for e in events
                    ],
                }
            )
        if changed:
            session.commit()
        return result


def purge_followups() -> int:
    """Expire anything overdue, then drop what has outlived its retention
    window, measured from terminal_at (never from created_at — a still-open
    attempt must not be swept just because it is old)."""
    now = _now()
    with SessionLocal() as session:
        overdue = (
            session.query(ChallengeAttemptRow)
            .filter(ChallengeAttemptRow.status == "PENDING", ChallengeAttemptRow.expires_at <= now)
            .all()
        )
        for attempt in overdue:
            _expire_if_due(session, attempt, now)
        session.commit()

        cutoff = now - timedelta(seconds=settings.challenge_followup_retention_seconds)
        expired_ids = select(ChallengeAttemptRow.attempt_id).where(
            ChallengeAttemptRow.terminal_at.isnot(None), ChallengeAttemptRow.terminal_at <= cutoff
        )
        session.query(ChallengeEventRow).filter(ChallengeEventRow.attempt_id.in_(expired_ids)).delete(
            synchronize_session=False
        )
        deleted = (
            session.query(ChallengeAttemptRow)
            .filter(ChallengeAttemptRow.terminal_at.isnot(None), ChallengeAttemptRow.terminal_at <= cutoff)
            .delete(synchronize_session=False)
        )
        session.commit()
    return deleted


def purge_idempotency_records() -> int:
    """Idempotency rows outlive their usefulness once no client could still be
    retrying with that key. Reuses `/v1/verify`'s own TTL setting — same
    purpose, same lifetime."""
    cutoff = _now() - timedelta(seconds=settings.idempotency_ttl_seconds)
    with SessionLocal() as session:
        deleted = (
            session.query(IdempotencyRecordRow)
            .filter(IdempotencyRecordRow.created_at <= cutoff)
            .delete(synchronize_session=False)
        )
        session.commit()
    return deleted
