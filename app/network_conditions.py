"""Congestion Insights as network condition INFORMATION, never as evidence.

The whole design rests on one separation. A congested cell explains why a
verification attempt was slow or failed; it says nothing about whether the
person is who they claim to be. So nothing in this module reaches a belief, a
risk score, a signed chain or a decision, and nothing here may waive a check.

Three other things it refuses to do, each because the alternative is a lie a UI
would happily tell:

  * an empty interval list is `unknown`, not `Low`;
  * a missing confidence is `None`, not 0 and not 100;
  * a create that succeeded is not proof that a notification was ever delivered.

Provider access is bounded the same way the rest of the adapter is: every call
carries an explicit timeout and no retries, and a query is refused unless a
subscription exists, because Nokia documents the subscription as a prerequisite.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.chain.subject import subject_hash
from app.config import settings
from app.db.database import SessionLocal
from app.db.models import NetworkConditionEventRow, NetworkConditionSubscriptionRow

# The vocabulary the operator documents. Anything else is `unknown` — the SDK
# does not constrain this field (see tests/test_nac_wire_contract.py), so an
# unexpected string reaches us verbatim and must not be rendered as a level.
LEVELS = {"low": "Low", "medium": "Medium", "high": "High"}

FORECAST = "forecast"
HISTORY = "history"

# Terminal states. A subscription in one of these makes no further provider
# calls and stops any polling a page is doing.
TERMINAL = {"deleted", "expired", "failed"}


class NetworkConditionError(RuntimeError):
    """A refusal with a stable machine code and no provider payload in it."""

    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass
class Interval:
    start: datetime
    stop: datetime
    level: str  # "Low" | "Medium" | "High" | "unknown"
    confidence: int | None  # None means the operator did not say


@dataclass
class QueryResult:
    mode: str  # forecast | history
    intervals: list[Interval] = field(default_factory=list)
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    provenance: str = "hosted_simulator"
    # True when the operator returned nothing at all. Kept distinct from "Low".
    empty: bool = True


def _now() -> datetime:
    return datetime.now(UTC)


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_level(raw: Any) -> str:
    """The operator's word, or `unknown`. Never a guess in either direction."""
    if not isinstance(raw, str):
        return "unknown"
    return LEVELS.get(raw.strip().lower(), "unknown")


def normalize_confidence(raw: Any) -> int | None:
    """A percentage the operator actually gave, or None.

    Turning a missing confidence into 0 invents certainty that the reading is
    worthless; turning it into 100 invents certainty that it is perfect. Both
    are claims nobody made.
    """
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    return raw if 0 <= raw <= 100 else None


def validate_period(start: datetime | None, end: datetime | None) -> str:
    """Decide forecast vs history, and refuse an unusable historical window.

    Both bounds absent is the upcoming forecast. Anything else must be an
    explicit, timezone-aware, chronological, bounded interval: a naive
    timestamp is an unanswerable question, and one bound alone silently means
    a fifteen-minute window on the other side that the caller did not ask for.
    """
    if start is None and end is None:
        return FORECAST
    if start is None or end is None:
        raise NetworkConditionError(
            "incomplete_period", "start and end must be given together"
        )
    for value, name in ((start, "start"), (end, "end")):
        if value.tzinfo is None or value.utcoffset() is None:
            raise NetworkConditionError(
                "naive_timestamp", f"{name} must carry a timezone offset"
            )
    if end <= start:
        raise NetworkConditionError("period_not_chronological", "end must be after start")
    span = end - start
    if span > timedelta(hours=settings.network_conditions_max_query_hours):
        raise NetworkConditionError(
            "period_too_long",
            f"the window may not exceed {settings.network_conditions_max_query_hours} hours",
        )
    return HISTORY


# --- ownership-scoped store --------------------------------------------------


def _row(session, subscription_id: str, owner_hash: str):
    """Only ever this owner's row. A missing row and another tenant's row are
    the same answer on purpose: existence is not something to leak."""
    return session.execute(
        select(NetworkConditionSubscriptionRow).where(
            NetworkConditionSubscriptionRow.subscription_id == subscription_id,
            NetworkConditionSubscriptionRow.owner_hash == owner_hash,
        )
    ).scalar_one_or_none()


def _effective_status(row: NetworkConditionSubscriptionRow, now: datetime) -> str:
    """Expiry is a fact about the clock, not a job that has to have run."""
    if row.status in TERMINAL:
        return row.status
    return "expired" if row.expires_at <= now else row.status


def _active_counts(session, owner_hash: str, device_hash: str, now: datetime):
    rows = session.execute(
        select(NetworkConditionSubscriptionRow).where(
            NetworkConditionSubscriptionRow.owner_hash == owner_hash
        )
    ).scalars()
    per_owner = 0
    per_device = 0
    for row in rows:
        if _effective_status(row, now) in TERMINAL:
            continue
        per_owner += 1
        if row.device_hash == device_hash:
            per_device += 1
    return per_owner, per_device


def as_public(row: NetworkConditionSubscriptionRow, now: datetime | None = None) -> dict:
    """What a caller may see. Never the provider id, never the callback token."""
    now = now or _now()
    status = _effective_status(row, now)
    return {
        "subscription_id": row.subscription_id,
        "status": status,
        "scope": row.scope,
        "created_at": row.created_at,
        "expires_at": row.expires_at,
        "terminal": status in TERMINAL,
        "reason": row.last_error or "",
    }


@dataclass
class CreatedSubscription:
    row_id: str
    callback_token: str


def create(
    owner_hash: str,
    phone_number: str,
    provider,
    now: datetime | None = None,
) -> dict:
    """Reserve a row, then ask the operator. In that order, deliberately.

    Writing our row first is what makes an uncertain create recoverable: if the
    provider call times out having actually succeeded, the row is already there
    to reconcile against a listing. The reverse order loses the subscription
    entirely and the usual "fix" is to create another one.
    """
    now = now or _now()
    if not settings.nac_congestion_callback_url:
        raise NetworkConditionError(
            "callback_not_configured",
            "no server-configured HTTPS callback exists for network conditions",
            status_code=503,
        )
    if not settings.nac_congestion_callback_url.startswith("https://"):
        raise NetworkConditionError(
            "callback_not_https", "the configured callback must be HTTPS", status_code=503
        )

    if not hasattr(provider, "create_congestion_subscription"):
        raise NetworkConditionError(
            "not_supported",
            "the configured provider does not offer network conditions",
            status_code=501,
        )

    device_hash = subject_hash(phone_number)
    ttl = timedelta(seconds=settings.nac_congestion_subscription_ttl_seconds)
    subscription_id = "ncs_" + uuid.uuid4().hex[:20]
    callback_token = secrets.token_urlsafe(32)

    with SessionLocal() as session:
        per_owner, per_device = _active_counts(session, owner_hash, device_hash, now)
        if per_owner >= settings.network_conditions_max_active_per_owner:
            raise NetworkConditionError(
                "too_many_subscriptions", "this account has too many active subscriptions"
            )
        if per_device >= settings.network_conditions_max_active_per_device:
            raise NetworkConditionError(
                "device_already_subscribed", "this device already has an active subscription"
            )
        session.add(
            NetworkConditionSubscriptionRow(
                subscription_id=subscription_id,
                owner_hash=owner_hash,
                provider_id=None,
                device_hash=device_hash,
                scope=_scope(),
                status="pending",
                created_at=now,
                expires_at=now + ttl,
                callback_token_digest=_token_digest(callback_token),
            )
        )
        session.commit()

    try:
        provider_id = provider.create_congestion_subscription(
            phone_number=phone_number,
            callback_url=settings.nac_congestion_callback_url,
            callback_token=callback_token,
            expires_at=now + ttl,
        )
    except NotImplementedError:
        # A provider that does not offer this at all. No operator was called and
        # no state exists anywhere, so the reservation is removed rather than
        # left as a "failed" row somebody would try to reconcile.
        _forget(subscription_id)
        raise NetworkConditionError(
            "not_supported",
            "the configured provider does not offer network conditions",
            status_code=501,
        ) from None
    except Exception as exc:  # noqa: BLE001 - never surface a provider payload
        _mark(subscription_id, status="failed", error=_code(exc))
        raise NetworkConditionError(
            "provider_unavailable",
            "the operator did not accept the subscription",
            status_code=502,
        ) from None

    _mark(subscription_id, status="active", provider_id=provider_id)
    with SessionLocal() as session:
        row = _row(session, subscription_id, owner_hash)
        return as_public(row, now)


def _scope() -> str:
    """Never inferred from a call that worked."""
    return "live_operator" if settings.provider == "nac" and _live_entitled() else "hosted_simulator"


def _live_entitled() -> bool:
    """Deliberately false until an operator says otherwise.

    There is no flag we can read that means "this account is on a live
    network"; the portal says Simulator. Guessing yes here would put
    `live_operator` on a record that never touched one.
    """
    return False


def _mark(subscription_id: str, **updates) -> None:
    with SessionLocal() as session:
        row = session.get(NetworkConditionSubscriptionRow, subscription_id)
        if row is None:
            return
        if "status" in updates:
            row.status = updates["status"]
        if "provider_id" in updates:
            row.provider_id = updates["provider_id"]
        if "error" in updates:
            row.last_error = (updates["error"] or "")[:120]
        if updates.get("deleted_at"):
            row.deleted_at = updates["deleted_at"]
        session.commit()


def _forget(subscription_id: str) -> None:
    """Remove a reservation for a call that never reached an operator."""
    with SessionLocal() as session:
        row = session.get(NetworkConditionSubscriptionRow, subscription_id)
        if row is not None:
            session.delete(row)
            session.commit()


def _code(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    return f"http_{status}" if isinstance(status, int) else type(exc).__name__[:40]


def get(owner_hash: str, subscription_id: str) -> dict | None:
    with SessionLocal() as session:
        row = _row(session, subscription_id, owner_hash)
        return as_public(row) if row is not None else None


def delete(owner_hash: str, subscription_id: str, provider, now: datetime | None = None) -> dict:
    """Idempotent, and honest when the operator would not let go.

    A second delete is a success. A failed provider delete is NOT: the row stays
    visible with the reason, because a subscription we could not remove is the
    one thing a caller most needs to know about.
    """
    now = now or _now()
    with SessionLocal() as session:
        row = _row(session, subscription_id, owner_hash)
        if row is None:
            raise NetworkConditionError("not_found", "no such subscription", status_code=404)
        already = row.status == "deleted"
        provider_id = row.provider_id

    if already:
        return get(owner_hash, subscription_id)

    if provider_id:
        try:
            provider.delete_congestion_subscription(provider_id)
        except Exception as exc:  # noqa: BLE001
            _mark(subscription_id, status="active", error=f"cleanup failed: {_code(exc)}")
            raise NetworkConditionError(
                "cleanup_failed",
                "the operator did not confirm deletion; the subscription may still exist",
                status_code=502,
            ) from None

    _mark(subscription_id, status="deleted", deleted_at=now, error="")
    return get(owner_hash, subscription_id)


def query(
    owner_hash: str,
    subscription_id: str,
    phone_number: str,
    provider,
    start: datetime | None = None,
    end: datetime | None = None,
    now: datetime | None = None,
) -> QueryResult:
    """One bounded provider read, and only behind a live subscription."""
    now = now or _now()
    mode = validate_period(start, end)

    with SessionLocal() as session:
        row = _row(session, subscription_id, owner_hash)
        if row is None:
            raise NetworkConditionError("not_found", "no such subscription", status_code=404)
        status = _effective_status(row, now)
        if status != "active":
            # Nokia documents the subscription as a prerequisite for a query,
            # so an expired or deleted one is a refusal here rather than a call
            # the operator would reject anyway.
            raise NetworkConditionError(
                "subscription_not_active",
                f"the subscription is {status}; create a new one before querying",
            )
        scope = row.scope

    try:
        raw = provider.query_congestion(phone_number=phone_number, start=start, end=end)
    except Exception:  # noqa: BLE001
        raise NetworkConditionError(
            "provider_unavailable", "the operator did not answer", status_code=502
        ) from None

    intervals = [
        Interval(
            start=item["start"],
            stop=item["stop"],
            level=normalize_level(item.get("level")),
            confidence=normalize_confidence(item.get("confidence")),
        )
        for item in raw or []
    ]
    return QueryResult(
        mode=mode,
        intervals=intervals,
        observed_at=now,
        provenance=scope,
        empty=not intervals,
    )


# --- callback ----------------------------------------------------------------


def accept_event(
    subscription_id: str,
    presented_token: str,
    event_id: str,
    level: Any,
    occurred_at: datetime,
    now: datetime | None = None,
) -> str:
    """Take one delivered notification, or say exactly why not.

    Returns "accepted", "duplicate" or raises. The distinction matters to the
    caller: a duplicate is a success for an at-least-once delivery, and turning
    it into an error invites the operator to retry forever.
    """
    now = now or _now()
    if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
        raise NetworkConditionError("naive_timestamp", "occurred_at must carry a timezone")

    with SessionLocal() as session:
        row = session.get(NetworkConditionSubscriptionRow, subscription_id)
        # A wrong id and a wrong token are one answer, and the token check runs
        # in constant time so neither can be found by timing the difference.
        expected = row.callback_token_digest if row is not None else ""
        presented = _token_digest(presented_token or "")
        authentic = hmac.compare_digest(expected, presented) if expected else False
        if row is None or not authentic:
            raise NetworkConditionError(
                "callback_unauthorized", "unknown subscription or token", status_code=401
            )
        if _effective_status(row, now) in TERMINAL:
            raise NetworkConditionError(
                "subscription_not_active", "the subscription is no longer active", status_code=410
            )

        age = (now - occurred_at).total_seconds()
        if age > settings.network_conditions_max_event_age_seconds:
            raise NetworkConditionError("event_stale", "the event is too old to apply")
        if age < -settings.network_conditions_max_event_age_seconds:
            raise NetworkConditionError("event_from_the_future", "the event postdates this server")

        existing = session.get(NetworkConditionEventRow, (subscription_id, event_id))
        if existing is not None:
            return "duplicate"

        stored = session.execute(
            select(NetworkConditionEventRow).where(
                NetworkConditionEventRow.subscription_id == subscription_id
            )
        ).scalars().all()
        newest = max((event.occurred_at for event in stored), default=None)
        if newest is not None and occurred_at < newest:
            # An older reading arriving late must not become the current
            # condition. It is refused rather than stored and sorted around.
            raise NetworkConditionError("event_out_of_order", "a newer event is already recorded")
        if len(stored) >= settings.network_conditions_max_events_per_subscription:
            # Bounded: a callback is an endpoint someone else calls.
            oldest = min(stored, key=lambda event: event.occurred_at)
            session.delete(oldest)

        session.add(
            NetworkConditionEventRow(
                subscription_id=subscription_id,
                event_id=event_id,
                level=normalize_level(level),
                occurred_at=occurred_at,
                received_at=now,
            )
        )
        session.commit()
        return "accepted"


def latest_event(owner_hash: str, subscription_id: str) -> dict | None:
    """The newest delivered notification for one of this owner's subscriptions."""
    with SessionLocal() as session:
        if _row(session, subscription_id, owner_hash) is None:
            return None
        events = session.execute(
            select(NetworkConditionEventRow).where(
                NetworkConditionEventRow.subscription_id == subscription_id
            )
        ).scalars().all()
        if not events:
            return None
        newest = max(events, key=lambda event: event.occurred_at)
        return {
            "event_id": newest.event_id,
            "level": newest.level,
            "occurred_at": newest.occurred_at,
            "received_at": newest.received_at,
        }
