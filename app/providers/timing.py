"""Normalizing a provider's swap timestamp into signed evidence metadata.

A date is a second, separately priced operator call whose answer is weaker than
it looks: it can be null, it can be an activation rather than a replacement, and
— observed on Nokia's hosted simulator on 2026-09-06 — it can contradict the
boolean the same account returned for the same number. This module turns all of
that into an explicit `EvidenceTiming`, and refuses to turn any of it into a
number the score can use.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.chain.models import EvidenceTiming
from app.domain.enums import Action

# A provider clock is not our clock. A timestamp a few minutes ahead of ours is
# ordinary skew between two machines; an hour ahead is not a real event time.
# Named, so the tolerance is a decision someone made rather than a magic number
# in a comparison.
FUTURE_TOLERANCE_SECONDS = 300

# The operator's field is "latest change". That can be the moment a subscriber
# first activated the SIM or first associated the handset, not a replacement of
# an earlier one. Rendered from a key so both languages say the same thing.
AMBIGUITY_LATEST_CHANGE = "swap_date_may_be_activation"

SOURCE_OPERATION = {
    Action.SIM_SWAP: "sim_swap.retrieve_date",
    Action.DEVICE_SWAP: "device_swap.retrieve_date",
}

# Only these two actions have a date operation at all.
TIMED_ACTIONS = frozenset(SOURCE_OPERATION)

# Signals whose boolean says a change happened inside the window. Only for
# those is a date outside the window a disagreement worth showing.
CHANGED_SIGNALS = {"SIM_SWAPPED", "DEVICE_SWAPPED"}


def now_utc() -> datetime:
    return datetime.now(UTC)


def unsupported(action: Action, reason: str = "provider has no date operation") -> EvidenceTiming:
    return EvidenceTiming(
        retrieved_at=now_utc(),
        source_operation=SOURCE_OPERATION.get(action, ""),
        availability="unsupported",
        reason=reason,
    )


def not_attempted(action: Action, reason: str) -> EvidenceTiming:
    return EvidenceTiming(
        retrieved_at=now_utc(),
        source_operation=SOURCE_OPERATION.get(action, ""),
        availability="not_attempted",
        reason=reason,
    )


def failure(action: Action, availability: str, reason: str) -> EvidenceTiming:
    return EvidenceTiming(
        retrieved_at=now_utc(),
        source_operation=SOURCE_OPERATION.get(action, ""),
        availability=availability,  # type: ignore[arg-type]
        reason=reason[:80],
    )


def normalize(
    action: Action,
    provider_time: object,
    retrieved_at: datetime,
    monitored_period_days: int | None = None,
) -> EvidenceTiming:
    """Turn one raw provider value into metadata, or into an explicit unknown.

    Every rejection below keeps the boolean evidence untouched. A date this
    function refuses is a date the UI shows as unknown — never a date it
    silently replaces with "no change".
    """
    base = {
        "retrieved_at": retrieved_at,
        "source_operation": SOURCE_OPERATION.get(action, ""),
        "monitored_period_days": monitored_period_days,
    }

    if provider_time is None:
        # An explicit null. The operator answered; it had no date to give.
        # This is NOT "never changed", and the difference is the whole point.
        return EvidenceTiming(
            **base, availability="no_date", reason="operator returned no date"
        )

    if not isinstance(provider_time, datetime):
        return EvidenceTiming(
            **base, availability="invalid", reason="value is not a timestamp"
        )

    if provider_time.tzinfo is None or provider_time.utcoffset() is None:
        # CAMARA requires a timezone. A naive value is an unanswerable question:
        # guessing UTC would invent an age that could be hours wrong.
        return EvidenceTiming(
            **base, availability="invalid", reason="timestamp carries no timezone"
        )

    age_seconds = (retrieved_at - provider_time).total_seconds()
    if age_seconds < -FUTURE_TOLERANCE_SECONDS:
        return EvidenceTiming(
            **base,
            availability="invalid",
            reason=f"timestamp is in the future beyond {FUTURE_TOLERANCE_SECONDS}s tolerance",
        )

    return EvidenceTiming(
        **base,
        provider_time=provider_time,
        # Clamped at zero: a value inside the skew tolerance is "just now", not
        # a negative age that would render as a change that has not happened.
        age_seconds_at_decision=max(age_seconds, 0.0),
        availability="available",
        ambiguity_key=AMBIGUITY_LATEST_CHANGE,
    )


def with_window_agreement(
    timing: EvidenceTiming, signal: str, max_age_hours: float | None
) -> EvidenceTiming:
    """Record whether the operator's two answers agree, without resolving it.

    The boolean and the date are separate observations. When the boolean says a
    change happened inside its window and the date sits outside that window,
    the honest thing to show a human is that the operator contradicted itself —
    not a verdict about which one to believe.
    """
    if (
        timing.availability != "available"
        or timing.age_seconds_at_decision is None
        or max_age_hours is None
        or signal not in CHANGED_SIGNALS
    ):
        return timing
    disagrees = timing.age_seconds_at_decision > max_age_hours * 3600
    return timing.model_copy(update={"disagrees_with_window": disagrees})
