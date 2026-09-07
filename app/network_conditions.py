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
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

# Aliased: this module has its own public `delete` (the subscription one).
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select

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

# A response is a reading, not a data export. An operator array longer than this
# is truncated rather than rendered.
MAX_INTERVALS = 96

# Clock skew between the caller and this server. A window starting a moment from
# now is a rounding difference; one starting tomorrow is a mistake.
FUTURE_PERIOD_TOLERANCE_SECONDS = 300

# Terminal states. A subscription in one of these makes no further provider
# calls and stops any polling a page is doing.
#
# `unknown` is deliberately NOT terminal. A create whose answer never arrived
# may have succeeded at the operator, so the row keeps consuming this device's
# capacity until somebody reconciles it — otherwise a timeout is an invitation
# to create a second remote subscription nobody will ever clean up.
TERMINAL = {"deleted", "expired", "failed"}

# Serializes the read-then-insert that enforces the per-owner and per-device
# caps, and the read-then-call that paces queries. Both are check-then-act, and
# the routes run them in worker threads, so two requests interleaved between the
# count and the insert produced two active subscriptions for one device.
#
# A process-local lock is the right scope for the documented single-worker
# deployment (see the Makefile's `serve` target) and no more: a multi-process
# deployment needs a database-level reservation, and this comment is here so
# that is a decision somebody makes rather than one they inherit.
_reservation = threading.Lock()


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
    if start > _now() + timedelta(seconds=FUTURE_PERIOD_TOLERANCE_SECONDS):
        # Two ordered bounds in the future are not history. Nokia's forecast is
        # the no-bounds call; asking for "history" that has not happened yet is
        # a question with no answer, and it should be refused rather than sent.
        raise NetworkConditionError(
            "period_in_the_future", "a historical window must start in the past"
        )
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
    if row.status in TERMINAL or row.status == "unknown":
        return row.status
    return "expired" if row.expires_at <= now else row.status


def _active_counts(session, owner_hash: str, device_hash: str, now: datetime):
    """How many live subscriptions this owner has, and how many on this device.

    The predicate is in the query, not in Python. This used to load every row
    an owner had ever created — including the terminal ones nothing was
    deleting (R07) — and discard almost all of them, so the cost of taking out
    a subscription grew with the number of subscriptions ever taken out. The
    (owner_hash, status, expires_at) index serves exactly this shape.

    `status NOT IN terminal AND expires_at > now` is `_effective_status` in SQL:
    expiry is a fact about the clock, so a row whose sweep has not run yet must
    not be counted as live here either.
    """
    live = (NetworkConditionSubscriptionRow.status == "unknown") | (
        NetworkConditionSubscriptionRow.status.notin_(tuple(TERMINAL))
        & (NetworkConditionSubscriptionRow.expires_at > now)
    )
    per_owner = session.execute(
        select(func.count())
        .select_from(NetworkConditionSubscriptionRow)
        .where(NetworkConditionSubscriptionRow.owner_hash == owner_hash, live)
    ).scalar_one()
    per_device = session.execute(
        select(func.count())
        .select_from(NetworkConditionSubscriptionRow)
        .where(
            NetworkConditionSubscriptionRow.owner_hash == owner_hash,
            NetworkConditionSubscriptionRow.device_hash == device_hash,
            live,
        )
    ).scalar_one()
    return per_owner, per_device


def purge_terminal(now: datetime | None = None) -> int:
    """Reclaim settled subscriptions and their events, in bounded batches.

    Nothing ever deleted these rows. Events were capped per subscription, so a
    repeated create/delete cycle grew the subscription table without limit and
    the event table with it — one bounded set of events per subscription, times
    an unbounded number of subscriptions (R07).

    Two rules shape what is *kept*:

      - a row is eligible only once it is settled AND older than the retention
        window, so a client that polls slowly can still read the terminal
        status it was waiting for;
      - `unknown` is never eligible. It means a create or delete may have left
        a subscription running at the operator that we failed to confirm, and
        that row is the only record anyone has that reconciliation is owed.
        Deleting it converts a known problem into a silent one, and into a
        subscription nobody will ever cancel.
    """
    now = now or _now()
    cutoff = now - timedelta(seconds=settings.network_condition_retention_seconds)
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(NetworkConditionSubscriptionRow)
                .where(
                    NetworkConditionSubscriptionRow.status.in_(tuple(TERMINAL)),
                    NetworkConditionSubscriptionRow.expires_at < cutoff,
                )
                .limit(settings.purge_batch_size)
            )
            .scalars()
            .all()
        )
        removed = 0
        for row in rows:
            session.execute(
                sql_delete(NetworkConditionEventRow).where(
                    NetworkConditionEventRow.subscription_id == row.subscription_id
                )
            )
            session.delete(row)
            removed += 1
        session.commit()
        return removed


def expire_due(now: datetime | None = None) -> int:
    """Write down the expiries the clock has already made true.

    `_effective_status` reports an expired subscription correctly without this,
    but the stored status is what the retention sweep and the indexed active
    count filter on. Without a job that settles them, a row that expired and
    was never read again would stay `active` in the table forever and never
    become eligible for retention.
    """
    now = now or _now()
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(NetworkConditionSubscriptionRow)
                .where(
                    NetworkConditionSubscriptionRow.status.notin_(tuple(TERMINAL)),
                    NetworkConditionSubscriptionRow.status != "unknown",
                    NetworkConditionSubscriptionRow.expires_at <= now,
                )
                .limit(settings.purge_batch_size)
            )
            .scalars()
            .all()
        )
        for row in rows:
            row.status = "expired"
        session.commit()
        return len(rows)


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


def callback_url_for(subscription_id: str) -> str:
    """Where the operator should POST events for THIS subscription.

    The configured value is a base; the subscription's own id is appended. A
    single static URL cannot say which subscription an event belongs to, which
    left the receiving route unable to find the row a real operator's POST was
    about — the tests passed only because they called the handler with an id
    they already knew.
    """
    return settings.nac_congestion_callback_base_url.rstrip("/") + "/" + subscription_id


def _require_callback() -> None:
    base = settings.nac_congestion_callback_base_url
    if not base:
        raise NetworkConditionError(
            "callback_not_configured",
            "no server-configured HTTPS callback exists for network conditions",
            status_code=503,
        )
    parsed = urlsplit(base)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise NetworkConditionError(
            "callback_not_https", "the configured callback must be HTTPS", status_code=503
        )


def _definitely_rejected(exc: Exception) -> bool:
    """Did the operator answer "no", or did we simply never hear back?

    A 4xx is an answer: nothing was created and nothing needs reconciling. A
    timeout, a connection failure or a 5xx is not — the subscription may exist
    at the operator, and treating that as a clean failure is how a demo leaks a
    subscription and then creates a second one on retry.
    """
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and 400 <= status < 500 and status != 408


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
    _require_callback()

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

    # Counting and inserting under one lock. Separately, two requests for the
    # same device interleaved between the count and the insert and both passed
    # a limit of one.
    with _reservation, SessionLocal() as session:
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
                provider_kind=settings.provider,
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
            callback_url=callback_url_for(subscription_id),
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
        if _definitely_rejected(exc):
            # The operator answered no. Nothing exists to reconcile, so the row
            # is terminal and stops consuming this device's capacity.
            _mark(subscription_id, status="failed", error=_code(exc))
            raise NetworkConditionError(
                "provider_rejected",
                "the operator refused the subscription",
                status_code=502,
            ) from None
        # We never heard back. The subscription may exist at the operator, so
        # the row stays NON-terminal: it keeps this device's capacity, and a
        # retry is refused until somebody reconciles it against the provider's
        # own listing. Creating a second one here is how the first is leaked.
        _mark(subscription_id, status="unknown", error=_code(exc))
        raise NetworkConditionError(
            "provider_unreachable",
            "the operator did not answer; this subscription may exist and must "
            "be reconciled before another is created",
            status_code=502,
        ) from None

    if not provider_id or not str(provider_id).strip():
        # An empty id is not a subscription we can read, delete or match a
        # callback to. Accepting it as `active` produced a row whose delete
        # skipped the provider entirely and reported success.
        _mark(subscription_id, status="unknown", error="operator returned no subscription id")
        raise NetworkConditionError(
            "provider_id_missing",
            "the operator returned no subscription id; the subscription must be "
            "reconciled before another is created",
            status_code=502,
        ) from None

    _mark(subscription_id, status="active", provider_id=str(provider_id))
    with SessionLocal() as session:
        row = _row(session, subscription_id, owner_hash)
        return as_public(row, now)


def _scope() -> str:
    """Where the data will actually come from, recorded at creation.

    Not inferred from a call that worked, and not flattened to one label. A
    reading produced by `MockProvider` is a fixture this repository wrote; a
    reading from the hosted Nokia simulator is an authenticated response from
    Nokia; neither is a live network. Labelling the first `hosted_simulator`
    was a claim about provenance that was simply untrue.
    """
    provider = settings.provider
    if provider == "mock":
        return "mock"
    if provider == "nac_fake":
        return "nac_fake"
    if provider == "hybrid":
        # Network conditions have no per-action live/mock split to route by,
        # and this provider does not offer them at all.
        return "unsupported"
    return "live_operator" if _live_entitled() else "hosted_simulator"


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


def list_owned(owner_hash: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Local recovery inventory. Listing never contacts the operator."""
    with SessionLocal() as session:
        rows = session.execute(
            select(NetworkConditionSubscriptionRow)
            .where(NetworkConditionSubscriptionRow.owner_hash == owner_hash)
            .order_by(NetworkConditionSubscriptionRow.created_at.desc(),
                      NetworkConditionSubscriptionRow.subscription_id)
            .limit(limit).offset(offset)
        ).scalars()
        return [as_public(row) for row in rows]


def reconcile(owner_hash: str, subscription_id: str, provider) -> dict:
    """Resolve a lost create response without issuing another remote create.

    A negative listing cannot establish that a timed-out write never happened;
    keep unknown records reserved until a matching remote ID is found.
    """
    with SessionLocal() as session:
        row = _row(session, subscription_id, owner_hash)
        if row is None:
            raise NetworkConditionError("not_found", "no such subscription", 404)
        if row.provider_kind != settings.provider:
            raise NetworkConditionError("provider_changed", "created by a different provider")
        if row.status != "unknown" or row.provider_id:
            return as_public(row)
    lookup = getattr(provider, "find_congestion_subscription", None)
    if not callable(lookup):
        raise NetworkConditionError("not_supported", "provider cannot reconcile subscriptions", 501)
    try:
        provider_id = lookup(callback_url_for(subscription_id))
    except Exception:  # noqa: BLE001 - any lookup failure leaves the record reserved
        # Deliberately opaque: the caller learns that remote state is still
        # unresolved, not how the operator's API failed. Narrowing this would
        # let an unlisted provider error fall through and mark a reserved
        # record resolved, which is the outcome reconciliation exists to avoid.
        raise NetworkConditionError(
            "reconciliation_failed", "operator state could not be reconciled", 502
        ) from None
    if not provider_id:
        return get(owner_hash, subscription_id)
    with _reservation, SessionLocal() as session:
        row = _row(session, subscription_id, owner_hash)
        if row is not None and row.status == "unknown" and not row.provider_id:
            row.provider_id = provider_id
            row.status = "active"
            row.last_error = ""
            session.commit()
        return as_public(row)


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
        if row.provider_kind and row.provider_kind != settings.provider:
            raise NetworkConditionError(
                "provider_changed", "this subscription was created by a different provider"
            )
        if not provider_id and row.status in {"pending", "unknown"}:
            raise NetworkConditionError(
                "reconciliation_required",
                "remote subscription state is unknown; reconcile before deleting",
                status_code=409,
            )

    if already:
        return get(owner_hash, subscription_id)

    if provider_id:
        try:
            provider.delete_congestion_subscription(provider_id)
        except Exception as exc:  # noqa: BLE001
            # A provider 404/410 confirms that there is nothing left to delete.
            if getattr(exc, "status_code", None) in {404, 410}:
                _mark(subscription_id, status="deleted", deleted_at=now, error="")
                return get(owner_hash, subscription_id)
            _mark(subscription_id, status="unknown", error=f"cleanup failed: {_code(exc)}")
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

    # The device check, the pacing check and the timestamp write happen under
    # one lock. Both were check-then-act: one subscription could be used to ask
    # about any number the same merchant liked, and two clicks in the same
    # second both reached the operator.
    with _reservation, SessionLocal() as session:
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
        if not hmac.compare_digest(row.device_hash, subject_hash(phone_number)):
            # The subscription is the prerequisite for asking about ONE device.
            # Owner isolation was enforced and this was not, so a merchant could
            # subscribe one number and then query every other number it liked
            # through the same subscription.
            raise NetworkConditionError(
                "device_not_subscribed",
                "this subscription is for a different device",
            )
        if row.provider_kind and row.provider_kind != settings.provider:
            raise NetworkConditionError(
                "provider_changed",
                "this subscription was created by a different provider",
            )
        if row.last_query_at is not None:
            elapsed = (now - row.last_query_at).total_seconds()
            minimum = settings.network_conditions_min_query_interval_seconds
            if elapsed < minimum:
                raise NetworkConditionError(
                    "query_too_soon",
                    f"wait {int(minimum - elapsed) + 1}s before asking again",
                    status_code=429,
                )
        # Written BEFORE the call, so a slow provider cannot be asked twice
        # while the first request is still in flight.
        row.last_query_at = now
        session.commit()
        scope = row.scope

    try:
        raw = provider.query_congestion(phone_number=phone_number, start=start, end=end)
    except Exception:  # noqa: BLE001
        raise NetworkConditionError(
            "provider_unavailable", "the operator did not answer", status_code=502
        ) from None

    intervals = _normalize_intervals(raw)
    return QueryResult(
        mode=mode,
        intervals=intervals,
        observed_at=now,
        provenance=scope,
        empty=not intervals,
    )


def _normalize_intervals(raw) -> list[Interval]:
    """Validate every interval before it becomes a response.

    A provider list is not trusted to be well formed: a missing key, a null
    timestamp or a reversed interval used to escape normalization and surface as
    a 500. Bad intervals are dropped rather than repaired — an interval we
    cannot read is not one we may show — and the count is bounded so an
    oversized array cannot become the response.
    """
    intervals: list[Interval] = []
    for item in list(raw or [])[:MAX_INTERVALS]:
        if not isinstance(item, dict):
            continue
        start, stop = item.get("start"), item.get("stop")
        if not isinstance(start, datetime) or not isinstance(stop, datetime):
            continue
        if start.tzinfo is None or stop.tzinfo is None:
            continue
        if stop <= start:
            continue
        intervals.append(
            Interval(
                start=start,
                stop=stop,
                level=normalize_level(item.get("level")),
                confidence=normalize_confidence(item.get("confidence")),
            )
        )
    return intervals


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
