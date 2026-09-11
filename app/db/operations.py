"""The durable half of `/v1/verify`'s idempotency (R13).

`app.cache` is an accelerator: it answers a repeat in microseconds and, under
Redis, answers it for every replica. It is not the record. The record is a row,
because the thing being protected is *money already spent at an operator*, and
a guarantee that evaporates on restart does not protect that.

The rule this module exists to enforce: a key is released only when nothing can
have been spent under it. Anything else — a crash, a cancellation, an error
raised once the investigation had begun — resolves to `uncertain`, which a
retry is refused rather than allowed to repeat.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import VerificationOperationRow

PENDING = "pending"
DONE = "done"
UNCERTAIN = "uncertain"


def key_digest(idempotency_key: str) -> str:
    """The caller's key is never stored in the clear: it is a caller-chosen
    string that routinely carries an order id."""
    return hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Operation:
    owner_hash: str
    key_hash: str
    request_hash: str
    state: str
    chain_id: str | None
    updated_at: datetime

    def is_orphaned(self, now: datetime | None = None) -> bool:
        """A `pending` row nobody is working on any more.

        There is no way to ask a process that has already died whether it
        reached the operator, so age is the only available signal: past the
        lease, a pending row is treated as `uncertain` rather than as a request
        still in flight. Erring the other way would re-charge.
        """
        if self.state != PENDING:
            return False
        now = now or datetime.now(UTC)
        return now - self.updated_at > timedelta(seconds=settings.idempotency_lease_seconds)


def _op(row: VerificationOperationRow) -> Operation:
    updated = row.updated_at
    if updated.tzinfo is None:  # SQLite hands back naive datetimes
        updated = updated.replace(tzinfo=UTC)
    return Operation(
        owner_hash=row.owner_hash,
        key_hash=row.key_hash,
        request_hash=row.request_hash,
        state=row.state,
        chain_id=row.chain_id,
        updated_at=updated,
    )


def reserve(owner_hash: str, key_hash: str, request_hash: str) -> Operation | None:
    """Claim the right to spend money under this key.

    Returns None when the claim succeeded. Returns the *existing* operation
    when it did not — the caller decides whether that is a replay, a conflict
    or a refusal, because only the caller knows the request it was asked to
    perform.
    """
    now = datetime.now(UTC)
    with SessionLocal() as s:
        s.add(
            VerificationOperationRow(
                owner_hash=owner_hash,
                key_hash=key_hash,
                request_hash=request_hash,
                state=PENDING,
                chain_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        try:
            s.commit()
            return None
        except IntegrityError:
            s.rollback()
        row = s.get(VerificationOperationRow, (owner_hash, key_hash))
        # The row can be gone again: a concurrent request may have released it
        # between our failed insert and this read. Reporting it as still in
        # progress is the conservative answer — the caller retries, and the
        # next attempt reserves cleanly.
        return _op(row) if row else Operation(owner_hash, key_hash, request_hash, PENDING, None, now)


def get(owner_hash: str, key_hash: str) -> Operation | None:
    with SessionLocal() as s:
        row = s.get(VerificationOperationRow, (owner_hash, key_hash))
        return _op(row) if row else None


def release(owner_hash: str, key_hash: str) -> bool:
    """Give a key back. Only ever called when nothing was spent under it.

    Deliberately narrow: this is the one path that lets a retry do billable
    work again, so it is used only where the failure provably preceded any
    provider call.
    """
    with SessionLocal() as s:
        row = s.get(VerificationOperationRow, (owner_hash, key_hash))
        if row is None or row.state != PENDING:
            return False
        s.delete(row)
        s.commit()
        return True


def mark_uncertain(owner_hash: str, key_hash: str) -> None:
    """Record that work under this key may have reached the operator.

    The row stays. A retry gets a stable refusal naming reconciliation, which
    is the honest answer: this service cannot say whether the call was made,
    and guessing costs the merchant real money in one direction and a
    duplicate charge in the other.
    """
    with SessionLocal() as s:
        row = s.get(VerificationOperationRow, (owner_hash, key_hash))
        if row is None or row.state != PENDING:
            return
        row.state = UNCERTAIN
        row.updated_at = datetime.now(UTC)
        s.commit()


def purge_expired() -> int:
    """Drop operations past the idempotency window, in bounded batches.

    `uncertain` rows are kept longer than settled ones on purpose: they are the
    only record that something may be owed at the operator, and deleting one
    turns an answerable question into a silent re-charge on the next retry.
    """
    now = datetime.now(UTC)
    settled = now - timedelta(seconds=settings.idempotency_ttl_seconds)
    unresolved = now - timedelta(seconds=settings.idempotency_uncertain_retention_seconds)
    with SessionLocal() as s:
        # Selected then deleted by primary key rather than deleted by
        # predicate: the key is composite, so a bounded `DELETE ... LIMIT` is
        # not portable across the SQLite demo path and a real database.
        rows = (
            s.execute(
                select(VerificationOperationRow)
                .where(
                    or_(
                        (VerificationOperationRow.state != UNCERTAIN)
                        & (VerificationOperationRow.updated_at < settled),
                        (VerificationOperationRow.state == UNCERTAIN)
                        & (VerificationOperationRow.updated_at < unresolved),
                    )
                )
                .limit(settings.purge_batch_size)
            )
            .scalars()
            .all()
        )
        for row in rows:
            s.delete(row)
        s.commit()
        return len(rows)


async def reserve_async(owner_hash: str, key_hash: str, request_hash: str) -> Operation | None:
    return await asyncio.to_thread(reserve, owner_hash, key_hash, request_hash)


async def get_async(owner_hash: str, key_hash: str) -> Operation | None:
    return await asyncio.to_thread(get, owner_hash, key_hash)


async def release_async(owner_hash: str, key_hash: str) -> bool:
    return await asyncio.to_thread(release, owner_hash, key_hash)


async def mark_uncertain_async(owner_hash: str, key_hash: str) -> None:
    await asyncio.to_thread(mark_uncertain, owner_hash, key_hash)
