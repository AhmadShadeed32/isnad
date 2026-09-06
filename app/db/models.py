from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.db.database import Base


class UtcDateTime(TypeDecorator):
    """A datetime column that is timezone-aware UTC on both sides.

    SQLite's DATETIME ignores tzinfo: an aware UTC value is written as its naive
    UTC components and READ BACK NAIVE. Everything in this app builds datetimes
    with `datetime.now(timezone.utc)`, so writes and SQL comparisons agreed and
    nothing was wrong — but subtracting a value read back from a row from an
    aware `now` raises TypeError, and that is a trap sitting under every future
    "how long is left on this?".

    Bind: normalize to UTC, then drop the tzinfo the backend would ignore
    anyway, so a value handed in as +03:00 is stored as the same instant rather
    than as its local clock face. Result: re-attach UTC. Rows written before
    this existed read back correctly, because they were already naive UTC.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=UTC)


class ChainRow(Base):
    """A persisted, signed evidence chain. Only chain evidence is stored — never
    raw network signals."""

    __tablename__ = "chains"

    chain_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    # sha256 of the API key that issued this chain. Every read and delete filters
    # on it: without it any key could fetch any other key's chain (S3). Chain ids
    # are 80 bits, so the exposure was horizontal rather than brute-forceable —
    # but with S1's published key the horizon was everyone.
    owner_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    decision: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    hypothesis: Mapped[str] = mapped_column(String(32))
    verdict_json: Mapped[str] = mapped_column(Text)  # exact bytes that were signed
    signature: Mapped[str] = mapped_column(Text)  # Ed25519, hex
    signed_at: Mapped[str] = mapped_column(String(40))
    public_key: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))


class CallAnnouncementRow(Base):
    """A call an institution said it was about to place — CAMARA VerifiedCaller.

    The inversion that makes a PBX call verifiable at all. No CAMARA API can
    attest a SIP trunk, because there is no SIM to ask about; so instead of
    interrogating the call, the institution announces it from an authenticated
    channel, and the callee's check asks whether a matching announcement exists.

    The callee is stored only as an HMAC under the subject pepper (S5). An
    institution announcing a call is telling this service who it is about to
    ring, and a plaintext column would turn that into a customer list.
    """

    __tablename__ = "call_announcements"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    # Which institution the announcing key is bound to. Never taken from the
    # request body: an announcement is only worth anything because the party
    # making it proved who they were, and a self-declared institution id would
    # hand any key holder the right to speak as a bank.
    institution_id: Mapped[str] = mapped_column(String(64), index=True)
    owner_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    # A pre-announcement only needs equality matching later; retaining the raw
    # calling number would create a second phone-number database for no benefit.
    calling_participant_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    called_participant_hash: Mapped[str] = mapped_column(String(64), index=True)
    strategy: Mapped[str] = mapped_column(String(24), default="BRAND_DISPLAY")
    display_name: Mapped[str] = mapped_column(String(120), default="")
    call_reason: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))
    # Absolute expiry rather than a TTL to add at read time: a row that has
    # outlived its window must be unusable even if the reader forgets to check,
    # and the spec's advice is a window measured in seconds.
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    # An announcement described ONE call. Left uncapped it verified every call
    # presenting that number for the length of its window, so a replayed or
    # leaked announcement was a free pass for a burst rather than for the single
    # call it was made about. Defaults so init_db's additive migration can add
    # both columns to an existing database.
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)


class ScreenEventRow(Base):
    """One Tier 1 screen, kept so velocity can be seen across subscribers.

    Every other check in this system judges a call in isolation. A scam campaign
    is not one call: it is one number reaching hundreds of people in minutes,
    and that shape is invisible to any single-call check no matter how good it
    is. This table is the only place that pattern can be seen — and it is the
    one signal here that gets stronger the more people use the system.

    The callee is an HMAC under the subject pepper, never a number. Counting
    DISTINCT callees needs to tell two people apart; it does not need to know
    who either of them is.
    """

    __tablename__ = "screen_events"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    # The velocity query needs a stable equality key, not the raw caller E.164.
    caller_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    callee_hash: Mapped[str] = mapped_column(String(64))
    # Which tenant observed this call. WITHOUT IT THE SIGNAL IS POISONABLE:
    # counting across every tenant let any key holder send ~30 screens with
    # invented callees and mark any bank's switchboard as a spoof for everybody
    # for the length of the window, and nothing recorded who did it.
    owner_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    at: Mapped[datetime] = mapped_column(UtcDateTime, index=True, default=lambda: datetime.now(UTC))

    # The velocity query filters on owner AND caller AND a time window. Separate
    # single-column indexes make SQLite pick one and scan the rest.
    __table_args__ = (Index("ix_screen_events_owner_caller_at", "owner_hash", "caller_hash", "at"),)


class ChallengeAttemptRow(Base):
    """One CHALLENGE followup: a merchant re-verifying a customer out of band
    after a signed CHALLENGE decision (P3).

    Deliberately its own table, never a column on `chains`: `ChainRow` is the
    thing the signature covers, and a followup happens strictly after that
    signature is fixed. Nothing here is ever folded back into `verdict_json`.
    """

    __tablename__ = "challenge_attempts"

    attempt_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    chain_id: Mapped[str] = mapped_column(String(40), index=True)
    owner_hash: Mapped[str] = mapped_column(String(64), index=True)
    method: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    # Stamped the moment status leaves PENDING (PASSED/FAILED/ABANDONED/EXPIRED),
    # by whichever transition wins the race. Retention is measured from this,
    # not from created_at — mirrors the consent store's terminal_at (P4a),
    # for the same reason: a still-open attempt must never be swept.
    terminal_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class ChallengeEventRow(Base):
    """One merchant-reported result against a `ChallengeAttemptRow`.

    Append-only. A conflicting second terminal result is rejected by the
    attempt's own compare-and-swap (P3), never overwritten here — this table
    only ever gains rows.
    """

    __tablename__ = "challenge_events"

    event_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(40), index=True)
    result: Mapped[str] = mapped_column(String(16))
    # Always "merchant_reported": the one other possible terminal cause,
    # server-side expiry, is recorded on the attempt itself and mints no event
    # row, since there is no merchant submission to attribute it to.
    provenance: Mapped[str] = mapped_column(String(24), default="merchant_reported")
    reported_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))


class IdempotencyRecordRow(Base):
    """A durable record of one merchant write, keyed by owner + operation +
    the caller's `Idempotency-Key` (P3).

    Unlike `/v1/verify`'s in-memory cache (app/cache.py), this must survive a
    restart: a merchant reporting a challenge outcome may not poll again for
    hours, and by then an in-memory reservation is long gone. The primary key
    IS the race resolution — two concurrent writes for the same key both try
    to insert this row, and the database's uniqueness constraint decides which
    one commits.
    """

    __tablename__ = "idempotency_records"

    owner_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    operation: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    # A keyed commitment to the full target + body (app.chain.subject.
    # idempotency_fingerprint) — never the raw request — so a key reused
    # against a different chain, attempt or body is detectable as a conflict.
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    response_json: Mapped[str] = mapped_column(Text)
    status_code: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))


class MerchantOutcomeEventRow(Base):
    """One merchant-reported outcome on an owned chain — order status or fraud
    assessment (P5). Challenge execution, the third dimension the handoff
    names, is deliberately NOT stored here: it is read from P3's own
    `ChallengeAttemptRow`/`ChallengeEventRow` when a report is assembled, so
    there is exactly one place that fact can come from.

    Append-only and self-superseding rather than updatable: a correction is a
    new row naming the row it replaces. The partial unique index below is what
    actually enforces "exactly one current (non-superseded) event per owner,
    chain and dimension" — the same reasoning as P3's CAS, extended to allow a
    caller-initiated correction rather than only a timeout.
    """

    __tablename__ = "merchant_outcome_events"

    event_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    chain_id: Mapped[str] = mapped_column(String(40), index=True)
    owner_hash: Mapped[str] = mapped_column(String(64), index=True)
    dimension: Mapped[str] = mapped_column(String(24))
    value: Mapped[str] = mapped_column(String(24))
    # Required for CONFIRMED_FRAUD/CONFIRMED_LEGITIMATE, absent otherwise —
    # enforced in the request schema, not here: a payment dispute or a lack of
    # feedback alone must never look like it justified a confirmed label.
    basis: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Merchant-supplied, bounded by a documented future-clock tolerance.
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime)
    # Server-owned; never taken from the request, so a report cannot be
    # backdated the way `signed_at` on a Verdict cannot (S5's same reasoning).
    reported_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))
    late_report: Mapped[bool] = mapped_column(Boolean, default=False)
    supersedes_event_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    # Kept as columns, not only in the shared `idempotency_records` table:
    # that table is TTL-purged (P3's own `purge_idempotency_records`), and an
    # outcome report is exactly the kind of record an audit needs to trace
    # back to its original request long after the idempotency window closes.
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_fingerprint: Mapped[str] = mapped_column(String(64))

    __table_args__ = (
        Index(
            "ux_outcome_current_per_dimension",
            "owner_hash",
            "chain_id",
            "dimension",
            unique=True,
            sqlite_where=text("superseded_by IS NULL"),
            postgresql_where=text("superseded_by IS NULL"),
        ),
    )


class AnnouncementUseRow(Base):
    """One subscriber's single use of one announcement.

    A global counter was worse than no counter. `find(consume=True)` spent the
    only use for whoever screened FIRST, and screening is open to any key
    holder — so an attacker could spray screens at (bank, victim) and burn every
    announcement the bank made, guaranteeing the victim's genuine calls always
    read UNKNOWN. The cap handed a third party a kill switch for the mechanism.

    Scoping the use to the reader fixes both directions: an attacker can only
    spend their own, and a reader who never screened a call cannot later mint an
    evidence chain from someone else's announcement.
    """

    __tablename__ = "announcement_uses"

    announcement_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    owner_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))


class ProofShareRow(Base):
    """An expiring reviewer link onto one chain's separately issued
    attestation (I13) — never a redacted copy of the original signature, and
    never a second way to reach the original `/r/{chain_id}` bytes.

    Insert-only in practice: `issued_at`/`expires_at` never change once set,
    so the attestation `sign_attestation()` recomputes from this row is
    byte-identical every time — nothing about it needs to be stored twice.
    Only `revoked_at` is ever written after creation, and only once.
    """

    __tablename__ = "proof_shares"

    share_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    # sha256 of the bearer token. The token itself is shown to the caller
    # exactly once (in the create response) and never stored in the clear.
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    chain_id: Mapped[str] = mapped_column(String(40), index=True)
    owner_hash: Mapped[str] = mapped_column(String(64), index=True)
    purpose: Mapped[str] = mapped_column(String(120), default="")
    scope: Mapped[str] = mapped_column(String(32), default="summary")
    issued_at: Mapped[datetime] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_fingerprint: Mapped[str] = mapped_column(String(64))


class RunEventRow(Base):
    """A durably persisted copy of one SSE event, keyed by (owner, run_id,
    sequence), so a reconnecting client can recover what it missed without
    rerunning the investigation (I14).

    Persisted BEFORE fan-out from `app.events.emit()`, and only for events
    that carry a `run_id` — most emissions in this app never do, and this
    table exists to serve replay, not to become a second copy of every event
    ever fired. `body` is allowlisted structured fields only (see
    `app.db.run_events._ALLOWED_BODY_KEYS`); a raw phone number, prompt or
    unrestricted provider string never reaches this table.
    """

    __tablename__ = "run_events"

    owner_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32))
    body_json: Mapped[str] = mapped_column(Text)
    server_time: Mapped[datetime] = mapped_column(UtcDateTime, index=True, default=lambda: datetime.now(UTC))


class NetworkConditionSubscriptionRow(Base):
    """One congestion subscription this service owns at the operator (gate 6).

    Network conditions are INFORMATION, not evidence: nothing in this table
    reaches a belief, a score or a signed chain. It exists so a subscription we
    created can be found again — reconciled after an uncertain write, read back,
    and above all deleted. A demo subscription that outlives the demo is a leak
    at somebody else's expense.

    The phone number is stored hashed under the same pepper as everything else:
    a device binding is needed to reject a callback about a subscriber we never
    asked about, and that does not require keeping the number.
    """

    __tablename__ = "network_condition_subscriptions"

    subscription_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    owner_hash: Mapped[str] = mapped_column(String(64), index=True)
    # What the operator called it. Null while a create is unreconciled — the
    # row is written BEFORE the provider call so an uncertain create can be
    # reconciled by listing rather than repeated blindly.
    provider_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    device_hash: Mapped[str] = mapped_column(String(64), index=True)
    # Which provider created this. A later configuration change must not let a
    # provider id minted by one backend be handed to another as if it were its
    # own — a mock id sent to Nokia is at best a 404 and at worst a delete of
    # somebody else's resource.
    provider_kind: Mapped[str] = mapped_column(String(24), default="")
    # "mock", "nac_fake", "hosted_simulator" or a separately verified live
    # scope. Never inferred from a successful call: it is what the configured
    # provider actually is, recorded when the subscription was created.
    scope: Mapped[str] = mapped_column(String(32), default="hosted_simulator")
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    # When this subscription last reached the provider for a reading. Queries
    # are paced against it: without one, a page that repeats a click bills the
    # operator once per click.
    last_query_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    # sha256 of the bearer token this subscription's callbacks must present.
    # Per subscription, so one leaked token cannot authenticate another's events.
    callback_token_digest: Mapped[str] = mapped_column(String(64))
    last_error: Mapped[str] = mapped_column(String(120), default="")


class NetworkConditionEventRow(Base):
    """One congestion notification delivered to our callback.

    Deduplicated by (subscription, event_id) and bounded per subscription, so a
    replayed or flooded callback cannot grow this table without limit. Stale and
    out-of-order events are rejected against `occurred_at` rather than stored
    and sorted later: an old reading arriving late must not become the current
    condition.
    """

    __tablename__ = "network_condition_events"

    subscription_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    level: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    received_at: Mapped[datetime] = mapped_column(UtcDateTime)
