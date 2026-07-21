from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.chain.models import Verdict
from app.chain.vault import vault
from app.db.database import SessionLocal, init_db
from app.db.models import ChainRow

# Ensure tables exist as soon as the store is used (idempotent).
init_db()


@dataclass
class ChainRecord:
    verdict: Verdict
    verdict_json: str
    signature: str
    signed_at: str
    public_key: str


def save(verdict: Verdict) -> ChainRecord:
    """Persist a chain, signing the exact stored JSON so it is tamper-evident."""
    verdict_json = verdict.model_dump_json()
    signature = vault.sign(verdict_json.encode("utf-8"))
    signed_at = vault.now_iso()
    public_key = vault.public_key_hex()
    with SessionLocal() as s:
        row = s.get(ChainRow, verdict.chain_id) or ChainRow(chain_id=verdict.chain_id)
        row.decision = verdict.decision.value
        row.confidence = verdict.confidence
        row.hypothesis = verdict.hypothesis
        row.verdict_json = verdict_json
        row.signature = signature
        row.signed_at = signed_at
        row.public_key = public_key
        s.add(row)
        s.commit()
    return ChainRecord(verdict, verdict_json, signature, signed_at, public_key)


def _record(row: ChainRow) -> ChainRecord:
    return ChainRecord(
        verdict=Verdict.model_validate_json(row.verdict_json),
        verdict_json=row.verdict_json,
        signature=row.signature,
        signed_at=row.signed_at,
        public_key=row.public_key,
    )


def get(chain_id: str) -> Optional[Verdict]:
    with SessionLocal() as s:
        row = s.get(ChainRow, chain_id)
        return _record(row).verdict if row else None


def get_record(chain_id: str) -> Optional[ChainRecord]:
    with SessionLocal() as s:
        row = s.get(ChainRow, chain_id)
        return _record(row) if row else None
