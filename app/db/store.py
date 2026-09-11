from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app.chain.models import Verdict
from app.chain.subject import owner_binding, subject_hash
from app.chain.vault import vault
from app.db.database import SessionLocal
from app.db.models import ChainRow, VerificationOperationRow
from app.events import current_owner
from app.ownership import ANONYMOUS


class ChainAlreadyExists(RuntimeError):
    """A second `save()` tried to reuse a chain_id that already has a signed
    record (P3).

    chain_id carries 80 bits of randomness, so a legitimate caller never
    collides with an existing one — this is either a bug or an attempt to
    rewrite a previously issued verdict, and both must fail loud rather than
    silently replace the decision, payload or signature a receipt was signed
    over.
    """


@dataclass
class ChainRecord:
    verdict: Verdict
    verdict_json: str
    signature: str
    signed_at: str
    public_key: str
    owner_hash: str = ""


def _owner() -> str:
    """The caller this request belongs to, set at the auth boundary (S2)."""
    return current_owner.get() or ANONYMOUS


def save(
    verdict: Verdict,
    subject: str | None = None,
    request_hash: str = "",
    operation: tuple[str, str] | None = None,
) -> ChainRecord:
    """Persist a chain, signing the exact stored JSON so it is tamper-evident.

    `subject` is the E.164 number the verdict is about. It is hashed here and
    discarded — the raw number never reaches the payload, the row, or a log —
    but the resulting binding goes *inside* the signed bytes, so the signature
    now says what it is evidence of (S5).

    signed_at is stamped onto the verdict before signing rather than kept as a
    sibling column. As a column it sat outside the signed bytes, so anyone with
    database write access could backdate a chain and verification still reported
    valid.

    `operation` is an (owner_hash, key_hash) pair naming the idempotency
    reservation this chain answers. Its completion is written in the SAME
    transaction as the chain, which is the whole point: the mapping from the
    caller's key to the signed result cannot be lost while the chain survives,
    so a crash can no longer leave a paid-for chain that the retry cannot find
    and therefore pays for again (R13).
    """
    owner = _owner()
    verdict.subject_hash = subject_hash(subject) if subject else ""
    verdict.owner_hash = owner_binding(owner)
    verdict.request_hash = request_hash
    verdict.signed_at = vault.now_iso()

    verdict_json = verdict.model_dump_json()
    signature = vault.sign(verdict_json.encode("utf-8"))
    signed_at = verdict.signed_at
    public_key = vault.public_key_hex()
    with SessionLocal() as s:
        # Insert-only (P3): a plain `s.get(...) or ChainRow(...)` upsert let a
        # colliding chain_id silently rewrite a signed decision. The unique
        # primary key is the enforcement; IntegrityError is how a race (two
        # concurrent saves of the same id) resolves rather than one winning
        # silently.
        s.add(
            ChainRow(
                chain_id=verdict.chain_id,
                owner_hash=owner,
                decision=verdict.decision.value,
                confidence=verdict.confidence,
                hypothesis=verdict.hypothesis,
                verdict_json=verdict_json,
                signature=signature,
                signed_at=signed_at,
                public_key=public_key,
            )
        )
        if operation is not None:
            row = s.get(VerificationOperationRow, operation)
            if row is not None:
                row.state = "done"
                row.chain_id = verdict.chain_id
                row.updated_at = datetime.now(UTC)
        try:
            s.commit()
        except IntegrityError as exc:
            s.rollback()
            raise ChainAlreadyExists(verdict.chain_id) from exc
    return ChainRecord(verdict, verdict_json, signature, signed_at, public_key, owner)


def _record(row: ChainRow) -> ChainRecord:
    return ChainRecord(
        verdict=Verdict.model_validate_json(row.verdict_json),
        verdict_json=row.verdict_json,
        signature=row.signature,
        signed_at=row.signed_at,
        public_key=row.public_key,
        owner_hash=row.owner_hash or "",
    )


def _owned(row: ChainRow | None) -> ChainRow | None:
    """A row the current caller is allowed to see, or None.

    None rather than a distinct error on purpose: the route turns it into the
    same 404 a missing chain gets, so an id cannot be probed for existence.
    """
    if row is None:
        return None
    if not secrets.compare_digest(row.owner_hash or "", _owner()):
        return None
    return row


def get(chain_id: str) -> Verdict | None:
    with SessionLocal() as s:
        row = _owned(s.get(ChainRow, chain_id))
        return _record(row).verdict if row else None


def get_record(chain_id: str) -> ChainRecord | None:
    with SessionLocal() as s:
        row = _owned(s.get(ChainRow, chain_id))
        return _record(row) if row else None


# --- async wrappers -----------------------------------------------------------
#
# The sync functions above are called from `async def` handlers in four routes.
# SQLite writes block, so each one stalled the event loop for the duration —
# which under any concurrency freezes the SSE stream feeding the console (S12).
# These run the same code on a worker thread. The ContextVar carrying the owner
# is copied into the thread by asyncio, so ownership still applies.


async def save_async(
    verdict: Verdict,
    subject: str | None = None,
    request_hash: str = "",
    operation: tuple[str, str] | None = None,
) -> ChainRecord:
    return await asyncio.to_thread(save, verdict, subject, request_hash, operation)


async def get_async(chain_id: str) -> Verdict | None:
    return await asyncio.to_thread(get, chain_id)


async def get_record_async(chain_id: str) -> ChainRecord | None:
    return await asyncio.to_thread(get_record, chain_id)


def get_public_record(chain_id: str) -> ChainRecord | None:
    """Read a chain WITHOUT the owner check, for the public receipt page (T6).

    A deliberate, single-purpose exception to S3, and the only one. It is safe
    for three reasons that all have to hold together:

      - chain_id is 80 bits of randomness, so the URL is an unguessable
        capability rather than an enumerable identifier;
      - the signed payload contains no PII by construction — no phone number, no
        raw provider payload, no coordinates (S5 kept it that way by binding to
        an HMAC rather than a number);
      - the receipt route renders only the grade, the decision and the link
        signals, and never the merchant it belongs to.

    Anything that needs to know *who* a chain belongs to must keep using get()
    or get_record(), which enforce ownership.
    """
    with SessionLocal() as s:
        row = s.get(ChainRow, chain_id)
        return _record(row) if row else None


async def get_public_record_async(chain_id: str) -> ChainRecord | None:
    return await asyncio.to_thread(get_public_record, chain_id)
