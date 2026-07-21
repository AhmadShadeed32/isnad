from __future__ import annotations

import hashlib
import secrets
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.domain.schemas import VerificationRequest, VerificationResponse


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _owner_hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


@dataclass
class ConsentRecord:
    consent_id: str
    state: str
    owner_hash: str
    request: VerificationRequest
    redirect_uri: str
    created_at: datetime
    expires_at: datetime
    status: str = "PENDING"
    authorization_url: Optional[str] = None
    access_token: Optional[str] = None
    chain_id: Optional[str] = None
    reason: Optional[str] = None
    response_json: Optional[str] = None


class ConsentStore:
    """Short-lived consent state; tokens never leave this process or API response."""

    def __init__(self) -> None:
        self._records: dict[str, ConsentRecord] = {}
        self._states: dict[str, str] = {}
        self._lock = threading.RLock()

    def create(
        self,
        request: VerificationRequest,
        api_key: str,
        redirect_uri: str,
        ttl_seconds: int,
    ) -> ConsentRecord:
        created_at = _now()
        record = ConsentRecord(
            consent_id="cns_" + uuid.uuid4().hex[:24],
            state=secrets.token_urlsafe(32),
            owner_hash=_owner_hash(api_key),
            request=request,
            redirect_uri=redirect_uri,
            created_at=created_at,
            expires_at=created_at + timedelta(seconds=ttl_seconds),
        )
        with self._lock:
            self._records[record.consent_id] = record
            self._states[record.state] = record.consent_id
        return record

    def by_state(self, state: str) -> Optional[ConsentRecord]:
        with self._lock:
            consent_id = self._states.get(state)
            record = self._records.get(consent_id) if consent_id else None
            self._expire(record)
            return record

    def owned(self, consent_id: str, api_key: str) -> Optional[ConsentRecord]:
        with self._lock:
            record = self._records.get(consent_id)
            self._expire(record)
            if record is None or not secrets.compare_digest(record.owner_hash, _owner_hash(api_key)):
                return None
            return record

    def set_authorization_url(self, record: ConsentRecord, url: str) -> None:
        with self._lock:
            if record.status == "PENDING":
                record.authorization_url = url

    def begin_callback(self, record: ConsentRecord) -> str:
        with self._lock:
            self._expire(record)
            if record.status == "PENDING":
                record.status = "EXCHANGING"
            return record.status

    def deny(self, record: ConsentRecord) -> None:
        with self._lock:
            self._expire(record)
            if record.status in {"PENDING", "EXCHANGING"}:
                record.status = "DENIED"
                record.reason = "user denied consent"

    def fail(self, record: ConsentRecord, reason: str) -> None:
        with self._lock:
            record.status = "FAILED"
            record.access_token = None
            record.reason = reason

    def authorize(self, record: ConsentRecord, access_token: str) -> None:
        with self._lock:
            self._expire(record)
            if record.status == "EXCHANGING":
                record.status = "AUTHORIZED"
                record.access_token = access_token

    def claim_verification(self, record: ConsentRecord) -> tuple[str, Optional[str]]:
        with self._lock:
            self._expire(record)
            if record.status == "COMPLETED":
                return "COMPLETED", record.response_json
            if record.status == "AUTHORIZED" and record.access_token:
                record.status = "VERIFYING"
                return "VERIFYING", record.access_token
            return record.status, None

    def complete(self, record: ConsentRecord, response: VerificationResponse) -> None:
        with self._lock:
            record.status = "COMPLETED"
            record.access_token = None
            record.chain_id = response.chain_id
            record.response_json = response.model_dump_json()
            record.reason = response.reason

    def fail_verification(self, record: ConsentRecord, reason: str) -> None:
        with self._lock:
            record.status = "FAILED"
            record.access_token = None
            record.reason = reason

    def public(self, record: ConsentRecord) -> dict:
        with self._lock:
            self._expire(record)
            return {
                "consent_id": record.consent_id,
                "status": record.status,
                "authorization_url": record.authorization_url,
                "expires_at": record.expires_at.isoformat(),
                "chain_id": record.chain_id,
                "reason": record.reason,
            }

    def _expire(self, record: Optional[ConsentRecord]) -> None:
        if record is None:
            return
        if record.expires_at <= _now() and record.status not in {"COMPLETED", "DENIED", "FAILED", "EXPIRED"}:
            record.status = "EXPIRED"
            record.access_token = None
            record.reason = "consent request expired"


consents = ConsentStore()
