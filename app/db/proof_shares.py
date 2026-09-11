"""Expiring reviewer links onto a separately issued attestation (I13).

A share's attestation is never the original signed Verdict, never a
selectively redacted copy of it, and never a second path to the original
`/r/{chain_id}` bytes: it is its own domain-separated, insert-only summary
(decision, grade, a digest of the source payload, issuance/expiry, issuer
key) signed with the same vault key under a different format. Revoking a
share disables future access through *that link* only — the original
receipt and anything already downloaded from it are unaffected.

Idempotency reuses P3's shared `IdempotencyRecordRow`, with one addition the
spec calls for specifically here: the create response contains a bearer
token that must be replayable, so unlike P3/P5 it is encrypted at rest under
a key derived from the vault's own pepper rather than stored in the clear.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet
from sqlalchemy.exc import IntegrityError

from app.chain.vault import vault
from app.db.database import SessionLocal
from app.db.models import IdempotencyRecordRow, ProofShareRow
from app.events import current_owner
from app.ownership import ANONYMOUS

_OPERATION = "proof_share.create"
ATTESTATION_TYPE = "isnad_proof_share_attestation_v1"


class IdempotencyKeyConflict(RuntimeError):
    pass


@dataclass
class WriteOutcome:
    response: dict
    status_code: int
    replayed: bool


def _owner() -> str:
    return current_owner.get() or ANONYMOUS


def _now() -> datetime:
    return datetime.now(UTC)


def _fernet() -> Fernet:
    """A symmetric key derived from the vault's own pepper. Not the pepper
    itself (that would leak it into a table an idempotency-TTL sweep touches)
    and not a fixed length assumption on `subject_pepper()` — this is always
    exactly 32 bytes before base64, whatever the configured pepper's length."""
    key_bytes = hashlib.sha256(vault.subject_pepper() + b"isnad/proof-share-idempotency/v1").digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _encrypt(response: dict) -> str:
    return _fernet().encrypt(json.dumps(response).encode("utf-8")).decode("ascii")


def _decrypt(token: str) -> dict:
    return json.loads(_fernet().decrypt(token.encode("ascii")).decode("utf-8"))


def create_share(
    *,
    chain_id: str,
    purpose: str,
    ttl_seconds: int,
    idempotency_key: str,
    fingerprint: str,
) -> WriteOutcome:
    owner = _owner()
    with SessionLocal() as session:
        existing = session.get(IdempotencyRecordRow, (owner, _OPERATION, idempotency_key))
        if existing is not None:
            if not hmac.compare_digest(existing.request_fingerprint, fingerprint):
                raise IdempotencyKeyConflict(idempotency_key)
            return WriteOutcome(_decrypt(existing.response_json), existing.status_code, replayed=True)

        now = _now()
        token = secrets.token_urlsafe(32)
        token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        share = ProofShareRow(
            share_id="pshare_" + uuid.uuid4().hex[:20],
            token_digest=token_digest,
            chain_id=chain_id,
            owner_hash=owner,
            purpose=purpose,
            scope="summary",
            issued_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            revoked_at=None,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
        )
        session.add(share)
        response = {
            "share_id": share.share_id,
            "chain_id": chain_id,
            "token": token,
            "purpose": purpose,
            "scope": "summary",
            "issued_at": share.issued_at.isoformat(),
            "expires_at": share.expires_at.isoformat(),
        }
        session.add(
            IdempotencyRecordRow(
                owner_hash=owner,
                operation=_OPERATION,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                response_json=_encrypt(response),
                status_code=201,
                created_at=now,
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            replay = session.get(IdempotencyRecordRow, (owner, _OPERATION, idempotency_key))
            if replay is None:
                raise
            if not hmac.compare_digest(replay.request_fingerprint, fingerprint):
                raise IdempotencyKeyConflict(idempotency_key) from None
            return WriteOutcome(_decrypt(replay.response_json), replay.status_code, replayed=True)
        return WriteOutcome(response, 201, replayed=False)


def revoke_share(*, chain_id: str, share_id: str) -> bool:
    """True if this call performed the revocation; False if the share did not
    exist for this owner/chain (a 404 to the caller) or was already revoked
    (still a success — revocation is idempotent by design)."""
    owner = _owner()
    with SessionLocal() as session:
        share = session.get(ProofShareRow, share_id)
        if share is None or share.chain_id != chain_id or not hmac.compare_digest(share.owner_hash, owner):
            return False
        if share.revoked_at is None:
            session.query(ProofShareRow).filter(
                ProofShareRow.share_id == share_id, ProofShareRow.revoked_at.is_(None)
            ).update({"revoked_at": _now()}, synchronize_session=False)
            session.commit()
        return True


def resolve_attestation(token: str) -> dict | None:
    """A currently-valid share's signed attestation, or None for missing,
    expired AND revoked alike — the same response either way, so a reader
    cannot distinguish "never existed" from "existed and was cut off"."""
    token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = _now()
    with SessionLocal() as session:
        share = session.query(ProofShareRow).filter(ProofShareRow.token_digest == token_digest).first()
        if share is None:
            return None
        if share.revoked_at is not None or share.expires_at <= now:
            return None

        from app.db.store import get_public_record

        record = get_public_record(share.chain_id)
        if record is None:
            return None
        verdict_json = record.verdict_json
        payload = {
            "type": ATTESTATION_TYPE,
            "share_id": share.share_id,
            "chain_id": share.chain_id,
            "decision": record.verdict.decision.value,
            "chain_grade": record.verdict.chain_grade.value if record.verdict.chain_grade else None,
            "source_payload_digest": hashlib.sha256(verdict_json.encode("utf-8")).hexdigest(),
            "issued_at": share.issued_at.isoformat(),
            "expires_at": share.expires_at.isoformat(),
            "issuer_public_key": vault.public_key_hex(),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        payload["signature"] = vault.sign(canonical)
        return payload


def purge_expired_shares() -> int:
    """Drop shares past their own expiry, revoked or not. This only removes
    the *link*; it can never affect the original chain or receipt."""
    cutoff = _now()
    with SessionLocal() as session:
        deleted = (
            session.query(ProofShareRow).filter(ProofShareRow.expires_at <= cutoff).delete(synchronize_session=False)
        )
        session.commit()
    return deleted
