from __future__ import annotations

import hashlib
import secrets
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.chain.subject import request_commitment
from app.config import settings
from app.domain.schemas import VerificationRequest, VerificationResponse

# Statuses that no longer accept a transition; a record in one of these is
# waiting only to be read (once) and then swept.
_TERMINAL = {"COMPLETED", "DENIED", "FAILED", "EXPIRED"}


def _now() -> datetime:
    return datetime.now(UTC)


def _owner_hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


@dataclass
class ConsentRecord:
    consent_id: str
    state: str
    # Separate from `state` (P4a): `state` round-trips through the provider's
    # authorization URL as CSRF protection, `nonce` is carried inside the
    # returned OIDC id_token and is never itself sent back to us in the query
    # string, so the two must not be the same value or a state-only replay
    # defense would also cover a forged/replayed id_token.
    nonce: str
    owner_hash: str
    request: VerificationRequest
    # Computed once, from the same frozen `request` snapshot, at creation —
    # never recomputed later from a `request` object a caller might still hold
    # a mutable reference to. See request_commitment()'s docstring.
    request_hash: str
    redirect_uri: str
    created_at: datetime
    expires_at: datetime
    status: str = "PENDING"
    authorization_url: str | None = None
    access_token: str | None = None
    chain_id: str | None = None
    reason: str | None = None
    response_json: str | None = None
    # Set the moment `status` first enters _TERMINAL. Retention is measured
    # from here, not from `created_at` or `expires_at` — a consent that takes
    # nearly its whole TTL to complete must still get its full retention
    # window afterwards.
    terminal_at: datetime | None = None


# Consent records were never swept except on access, so a stream of started-
# and-abandoned consents grew the map for the life of the process (S12).
MAX_CONSENT_RECORDS = 1000
# A single merchant must not be able to reserve the process-wide consent map.
# More importantly, a full map must never evict someone else's still-valid
# authorization state: eviction turns a legitimate provider callback into a
# confusing 404 and enables cross-tenant denial of service.
MAX_CONSENT_RECORDS_PER_OWNER = 50


class ConsentCapacityExceeded(RuntimeError):
    """A live consent cannot be retained without displacing another one."""


class ConsentStore:
    """Short-lived consent state; tokens never leave this process or API response."""

    def __init__(
        self,
        max_records: int = MAX_CONSENT_RECORDS,
        max_records_per_owner: int = MAX_CONSENT_RECORDS_PER_OWNER,
        terminal_retention_seconds: int | None = None,
    ) -> None:
        self._records: dict[str, ConsentRecord] = {}
        self._states: dict[str, str] = {}
        self._lock = threading.RLock()
        self.max_records = max_records
        self.max_records_per_owner = max_records_per_owner
        self.terminal_retention_seconds = (
            settings.nac_consent_terminal_retention_seconds
            if terminal_retention_seconds is None
            else terminal_retention_seconds
        )

    def create(
        self,
        request: VerificationRequest,
        api_key: str,
        redirect_uri: str,
        ttl_seconds: int,
    ) -> ConsentRecord:
        created_at = _now()
        owner = _owner_hash(api_key)
        # Snapshot the request now, deep-copied, and commit to it now. A
        # caller that still holds `request` and mutates it afterwards (or a
        # future code path that reassigns `record.request`) must not be able
        # to change what the eventual receipt's request_hash attests to.
        frozen_request = request.model_copy(deep=True)
        record = ConsentRecord(
            consent_id="cns_" + uuid.uuid4().hex[:24],
            state=secrets.token_urlsafe(32),
            nonce=secrets.token_urlsafe(32),
            owner_hash=owner,
            request=frozen_request,
            request_hash=request_commitment(frozen_request),
            redirect_uri=redirect_uri,
            created_at=created_at,
            expires_at=created_at + timedelta(seconds=ttl_seconds),
        )
        with self._lock:
            self._sweep()
            owner_count = sum(
                1 for existing in self._records.values() if existing.owner_hash == owner
            )
            if owner_count >= self.max_records_per_owner:
                raise ConsentCapacityExceeded("consent limit reached for this merchant")
            if len(self._records) >= self.max_records:
                raise ConsentCapacityExceeded("consent capacity is temporarily full")
            self._records[record.consent_id] = record
            self._states[record.state] = record.consent_id
        return record

    def _past_terminal_retention(self, record: ConsentRecord, now: datetime) -> bool:
        if record.status not in _TERMINAL:
            return False
        retain_until = (record.terminal_at or now) + timedelta(seconds=self.terminal_retention_seconds)
        return now >= retain_until

    def _drop(self, consent_id: str, record: ConsentRecord) -> None:
        del self._records[consent_id]
        self._states.pop(record.state, None)

    def _sweep(self) -> int:
        """Drop terminal records once their retention window has passed.

        Caller holds the lock. Every record is offered to _expire() first, so
        one past its TTL that nobody polled is promoted to EXPIRED (and given
        a terminal_at) before the retention check runs — otherwise it would
        wait here forever, since only a terminal record is ever swept. A
        record must survive being terminal for `terminal_retention_seconds`:
        completing consent B must not make consent A's just-issued result
        vanish mid-poll because A also happened to be terminal.

        R4: this used to be the ONLY place terminal retention was enforced,
        and its only caller was `create()` — a merchant polling a long-idle
        terminal consent with no one else creating new consents would get it
        back forever. `owned()`/`by_state()` now apply the same predicate
        inline on every read (see `_past_terminal_retention`), and this sweep
        is also exposed as `purge_expired()` for the periodic retention
        service, so an otherwise-idle process still reclaims these records.
        """
        now = _now()
        deleted = 0
        for consent_id, record in list(self._records.items()):
            self._expire(record, now=now)
            if self._past_terminal_retention(record, now):
                self._drop(consent_id, record)
                deleted += 1
        return deleted

    def purge_expired(self) -> int:
        """Lock-safe entry point for `app.retention`'s periodic sweeper."""
        with self._lock:
            return self._sweep()

    def by_state(self, state: str) -> ConsentRecord | None:
        with self._lock:
            consent_id = self._states.get(state)
            record = self._records.get(consent_id) if consent_id else None
            now = _now()
            self._expire(record, now=now)
            if record is not None and self._past_terminal_retention(record, now):
                self._drop(consent_id, record)
                return None
            return record

    def owned(self, consent_id: str, api_key: str) -> ConsentRecord | None:
        with self._lock:
            record = self._records.get(consent_id)
            now = _now()
            self._expire(record, now=now)
            if record is not None and self._past_terminal_retention(record, now):
                self._drop(consent_id, record)
                record = None
            if record is None or not secrets.compare_digest(
                record.owner_hash, _owner_hash(api_key)
            ):
                return None
            return record

    def set_authorization_url(self, record: ConsentRecord, url: str) -> None:
        with self._lock:
            if record.status == "PENDING":
                record.authorization_url = url

    # Returned when a callback arrives for a state that has already been used.
    # It has to be distinguishable from "I just promoted this one", which is what
    # the old code could not express (S9).
    REPLAYED = "REPLAYED"

    def begin_callback(self, record: ConsentRecord) -> str:
        """Claim this consent for exactly one callback.

        A true compare-and-swap. The old version promoted PENDING -> EXCHANGING
        and then returned record.status, so a second callback on an already-
        EXCHANGING record also returned "EXCHANGING" and the 409 guard in the
        route could never fire. Combined with by_state() still resolving after
        use, an attacker who observed the state — it is in the authorization URL
        the console window.open()s — could replay the callback with their own
        code; whichever exchange landed first won, binding the attacker's Number
        Verification token into the merchant's consent record, which then drives
        investigate().
        """
        with self._lock:
            self._expire(record)
            if record.status != "PENDING":
                # Includes a second callback on an EXCHANGING record, which is
                # the replay. AUTHORIZED/COMPLETED/EXPIRED are returned as
                # themselves so the route can answer them idempotently.
                if record.status == "EXCHANGING":
                    return self.REPLAYED
                return record.status
            record.status = "EXCHANGING"
            # Single-use: the state stops resolving the moment it is claimed.
            self._states.pop(record.state, None)
            return record.status

    def deny(self, record: ConsentRecord) -> None:
        with self._lock:
            self._expire(record)
            self._states.pop(record.state, None)  # single-use, like the success path
            if record.status in {"PENDING", "EXCHANGING"}:
                record.status = "DENIED"
                record.access_token = None
                record.reason = "user denied consent"
                record.terminal_at = _now()

    def fail(self, record: ConsentRecord, reason: str) -> None:
        with self._lock:
            record.status = "FAILED"
            record.access_token = None
            record.reason = reason
            record.terminal_at = _now()

    def authorize(self, record: ConsentRecord, access_token: str) -> None:
        with self._lock:
            self._expire(record)
            if record.status == "EXCHANGING":
                record.status = "AUTHORIZED"
                record.access_token = access_token

    def claim_verification(self, record: ConsentRecord) -> tuple[str, str | None]:
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
            record.terminal_at = _now()

    def fail_verification(self, record: ConsentRecord, reason: str) -> None:
        with self._lock:
            record.status = "FAILED"
            record.access_token = None
            record.reason = reason
            record.terminal_at = _now()

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

    def _expire(self, record: ConsentRecord | None, now: datetime | None = None) -> None:
        if record is None:
            return
        now = now or _now()
        if record.expires_at <= now and record.status not in _TERMINAL:
            record.status = "EXPIRED"
            record.access_token = None
            record.reason = "consent request expired"
            record.terminal_at = now


consents = ConsentStore()
