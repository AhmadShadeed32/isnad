"""Merchant-reported outcomes (P5): what actually happened, collected before
any score calibration leans on it.

Two dimensions live here — order status and fraud assessment. The third the
handoff names, challenge execution, is deliberately not stored here: it comes
from P3's own `ChallengeAttemptRow`/`ChallengeEventRow`, read fresh whenever a
report is assembled (see `challenge_execution_summary` below), so there is
exactly one place that fact can come from.

Corrections are appended, never applied as an UPDATE: `report()` either
creates the first (non-superseding) event for a dimension, or names the
current head it replaces. The partial unique index on `MerchantOutcomeEventRow`
is the actual enforcement of "exactly one current event per owner, chain and
dimension" — this module's own read-then-write checks are the friendly error
path, not the race resolution.
"""

from __future__ import annotations

import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import (
    ChallengeAttemptRow,
    ChallengeEventRow,
    IdempotencyRecordRow,
    MerchantOutcomeEventRow,
)
from app.events import current_owner
from app.ownership import ANONYMOUS

_OPERATION = "outcome.report"


class DimensionAlreadyLabelled(RuntimeError):
    """A current event already exists for this (owner, chain, dimension); the
    request must name it via supersedes_event_id to correct it."""


class SupersedeTargetNotFound(RuntimeError):
    """supersedes_event_id does not name the current head for this owner,
    chain and dimension — missing, foreign, already superseded, or a
    concurrent correction won the race first."""


class IdempotencyKeyConflict(RuntimeError):
    """The Idempotency-Key was already used for a different target or body."""


@dataclass
class WriteOutcome:
    response: dict
    status_code: int
    replayed: bool


def _owner() -> str:
    return current_owner.get() or ANONYMOUS


def _now() -> datetime:
    return datetime.now(UTC)


def _event_dict(event: MerchantOutcomeEventRow) -> dict:
    return {
        "event_id": event.event_id,
        "chain_id": event.chain_id,
        "dimension": event.dimension,
        "value": event.value,
        "basis": event.basis,
        "occurred_at": event.occurred_at.isoformat(),
        "reported_at": event.reported_at.isoformat(),
        "late_report": event.late_report,
        "supersedes_event_id": event.supersedes_event_id,
    }


def _current_head(session, chain_id: str, owner: str, dimension: str) -> MerchantOutcomeEventRow | None:
    return (
        session.query(MerchantOutcomeEventRow)
        .filter(
            MerchantOutcomeEventRow.chain_id == chain_id,
            MerchantOutcomeEventRow.owner_hash == owner,
            MerchantOutcomeEventRow.dimension == dimension,
            MerchantOutcomeEventRow.superseded_by.is_(None),
        )
        .first()
    )


def report(
    *,
    chain_id: str,
    dimension: str,
    value: str,
    basis: str | None,
    occurred_at: datetime,
    late_report: bool,
    supersedes_event_id: str | None,
    idempotency_key: str,
    fingerprint: str,
) -> WriteOutcome:
    owner = _owner()
    with SessionLocal() as session:
        existing = session.get(IdempotencyRecordRow, (owner, _OPERATION, idempotency_key))
        if existing is not None:
            if not hmac.compare_digest(existing.request_fingerprint, fingerprint):
                raise IdempotencyKeyConflict(idempotency_key)
            return WriteOutcome(json.loads(existing.response_json), existing.status_code, replayed=True)

        current = _current_head(session, chain_id, owner, dimension)
        if current is None:
            if supersedes_event_id is not None:
                raise SupersedeTargetNotFound(supersedes_event_id)
        elif supersedes_event_id != current.event_id:
            if supersedes_event_id is None:
                raise DimensionAlreadyLabelled(dimension)
            raise SupersedeTargetNotFound(supersedes_event_id)

        now = _now()
        event = MerchantOutcomeEventRow(
            event_id="mout_" + uuid.uuid4().hex[:20],
            chain_id=chain_id,
            owner_hash=owner,
            dimension=dimension,
            value=value,
            basis=basis,
            occurred_at=occurred_at,
            reported_at=now,
            late_report=late_report,
            supersedes_event_id=supersedes_event_id,
            superseded_by=None,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
        )
        session.add(event)

        if current is not None:
            # The actual race resolution for "competing corrections": only the
            # current head is supersedable, so this single CAS also rejects a
            # stale correction and a concurrent one racing this same request.
            updated = (
                session.query(MerchantOutcomeEventRow)
                .filter(
                    MerchantOutcomeEventRow.event_id == current.event_id,
                    MerchantOutcomeEventRow.superseded_by.is_(None),
                )
                .update({"superseded_by": event.event_id}, synchronize_session=False)
            )
            if not updated:
                session.rollback()
                raise SupersedeTargetNotFound(supersedes_event_id)

        response = _event_dict(event)
        session.add(
            IdempotencyRecordRow(
                owner_hash=owner,
                operation=_OPERATION,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                response_json=json.dumps(response),
                status_code=201,
                created_at=now,
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            # Two possible causes share this exception: a concurrent retry of
            # the same idempotency key, or two concurrent *first* reports on
            # the same dimension colliding on the partial unique index (no
            # `current` existed for either to check against). Disambiguate by
            # whether the idempotency row exists now.
            replay = session.get(IdempotencyRecordRow, (owner, _OPERATION, idempotency_key))
            if replay is not None:
                if not hmac.compare_digest(replay.request_fingerprint, fingerprint):
                    raise IdempotencyKeyConflict(idempotency_key) from None
                return WriteOutcome(json.loads(replay.response_json), replay.status_code, replayed=True)
            raise DimensionAlreadyLabelled(dimension) from None
        return WriteOutcome(response, 201, replayed=False)


def current_and_timeline(*, chain_id: str) -> dict:
    owner = _owner()
    with SessionLocal() as session:
        heads = (
            session.query(MerchantOutcomeEventRow)
            .filter(
                MerchantOutcomeEventRow.chain_id == chain_id,
                MerchantOutcomeEventRow.owner_hash == owner,
                MerchantOutcomeEventRow.superseded_by.is_(None),
            )
            .all()
        )
        timeline = (
            session.query(MerchantOutcomeEventRow)
            .filter(MerchantOutcomeEventRow.chain_id == chain_id, MerchantOutcomeEventRow.owner_hash == owner)
            .order_by(MerchantOutcomeEventRow.reported_at.asc())
            .all()
        )
        return {
            "current": {h.dimension: _event_dict(h) for h in heads},
            "timeline": [_event_dict(e) for e in timeline],
        }


def challenge_execution_summary(*, chain_id: str, owner: str) -> dict | None:
    """The challenge_execution dimension, read fresh from P3's own tables
    rather than duplicated into a MerchantOutcomeEventRow. Returns the most
    recently created attempt's status, or None if no attempt was ever opened.
    """
    with SessionLocal() as session:
        attempt = (
            session.query(ChallengeAttemptRow)
            .filter(ChallengeAttemptRow.chain_id == chain_id, ChallengeAttemptRow.owner_hash == owner)
            .order_by(ChallengeAttemptRow.created_at.desc())
            .first()
        )
        if attempt is None:
            return None
        events = (
            session.query(ChallengeEventRow)
            .filter(ChallengeEventRow.attempt_id == attempt.attempt_id)
            .order_by(ChallengeEventRow.reported_at.asc())
            .all()
        )
        return {
            "attempt_id": attempt.attempt_id,
            "status": attempt.status,
            "reported_at": events[-1].reported_at.isoformat() if events else None,
        }


def purge_outcomes() -> int:
    """Purge by server-reported time, current heads included: a dimension
    whose only events have aged out simply reverts to "not yet reported" —
    the retention window is explicit, not a promise this label survives it."""
    cutoff = _now() - timedelta(seconds=settings.outcome_retention_seconds)
    with SessionLocal() as session:
        deleted = (
            session.query(MerchantOutcomeEventRow)
            .filter(MerchantOutcomeEventRow.reported_at <= cutoff)
            .delete(synchronize_session=False)
        )
        session.commit()
    return deleted
