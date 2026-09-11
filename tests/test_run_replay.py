"""I14 — durable trace recovery after a disconnect.

Events are persisted before fan-out, keyed by (owner, run_id, sequence), so a
reconnecting client can recover what it missed without rerunning — and
without buying the checks again — while a client that never disconnected
keeps working exactly as before.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.db import run_events
from app.events import current_owner, emit


@pytest.fixture(autouse=True)
def _owner():
    token = current_owner.set("run-replay-owner")
    yield
    current_owner.reset(token)


@pytest.mark.asyncio
async def test_an_event_with_a_run_id_is_persisted():
    await emit({"type": "start", "run_id": "run_a", "chain_id": "chn_x"})
    events = run_events.events_after("run-replay-owner", "run_a", after=0)
    assert len(events) == 1
    assert events[0]["sequence"] == 1
    assert events[0]["event_type"] == "start"


@pytest.mark.asyncio
async def test_an_event_with_no_run_id_is_never_persisted():
    await emit({"type": "start", "chain_id": "chn_y"})
    events = run_events.events_after("run-replay-owner", "", after=0)
    assert events == []


@pytest.mark.asyncio
async def test_sequence_numbers_are_monotonic_and_gapless_per_run():
    for i in range(5):
        await emit({"type": "evidence", "run_id": "run_b", "step": i})
    events = run_events.events_after("run-replay-owner", "run_b", after=0)
    assert [e["sequence"] for e in events] == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_after_cursor_only_returns_newer_events():
    for i in range(3):
        await emit({"type": "evidence", "run_id": "run_c", "step": i})
    events = run_events.events_after("run-replay-owner", "run_c", after=1)
    assert [e["sequence"] for e in events] == [2, 3]


@pytest.mark.asyncio
async def test_a_foreign_owner_sees_no_events_for_the_run():
    await emit({"type": "start", "run_id": "run_d"})
    events = run_events.events_after("someone-else", "run_d", after=0)
    assert events == []


@pytest.mark.asyncio
async def test_concurrent_runs_never_produce_duplicate_or_out_of_order_sequences():
    """Two runs writing at the same time may contend for SQLite's single
    writer lock; persist_event's own explicit behavior under that contention
    is to drop the losing write (never raise into the live investigation,
    never assign a duplicate or decreasing sequence — see persist_event's own
    docstring). The unique (owner, run_id, sequence) constraint is what makes
    a collision impossible to hide, not a promise that no write is ever lost
    under contention."""

    async def one_run(run_id: str, n: int) -> None:
        for i in range(n):
            await emit({"type": "evidence", "run_id": run_id, "step": i})

    await asyncio.gather(one_run("run_e1", 4), one_run("run_e2", 4))
    e1 = run_events.events_after("run-replay-owner", "run_e1", after=0)
    e2 = run_events.events_after("run-replay-owner", "run_e2", after=0)

    for events in (e1, e2):
        sequences = [e["sequence"] for e in events]
        assert sequences == sorted(set(sequences)), "no duplicate or out-of-order sequence"
        assert len(events) >= 1, "at least one write per run must have survived"


@pytest.mark.asyncio
async def test_only_allowlisted_fields_are_persisted_in_the_body():
    await emit(
        {
            "type": "evidence",
            "run_id": "run_f",
            "signal": "SIM_SWAPPED",
            "detail": "a normalized sentence",
            "phone_number": "+15551234567",
        }
    )
    events = run_events.events_after("run-replay-owner", "run_f", after=0)
    body = events[0]["body"]
    assert "phone_number" not in body
    assert body.get("signal") == "SIM_SWAPPED"


@pytest.mark.asyncio
async def test_the_enrichment_row_keeps_its_structured_fields_and_nothing_else():
    """A recovered swap-date row used to render an empty heading.

    `enrichment` carries the operator's answer as bounded structured values —
    an availability enum, an operation name, a timestamp, two numbers and a
    boolean — and none of them were persisted, so replay drew a row that said a
    separate operator call had happened and could not say what it returned. The
    fields below are what the row is made of; everything asserted absent is
    what a journal that outlives the request must never hold.
    """
    await emit(
        {
            "type": "enrichment",
            "run_id": "run_enrich",
            "step": 2,
            "api": "sim-swap",
            "operation": "retrieve-date",
            "availability": "available",
            "provider_time": "2026-09-01T10:00:00+00:00",
            "age_seconds": 93600,
            "monitored_period_days": 120,
            "disagrees_with_window": True,
            "reason": "operator returned no date",
            "cost": 2.0,
            # None of these are the row's content, and each one is a way the
            # journal could start holding something it has no business keeping.
            "detail": "SIM replaced on 1 September per our records",
            "phone_number": "+962790000002",
            "prompt": "You are a fraud analyst. The subscriber is...",
            "exception": "ConnectionError: [Errno 111] to 10.0.0.4:443",
        }
    )
    events = run_events.events_after("run-replay-owner", "run_enrich", after=0)
    body = events[0]["body"]

    assert body["availability"] == "available"
    assert body["operation"] == "retrieve-date"
    assert body["provider_time"] == "2026-09-01T10:00:00+00:00"
    assert body["age_seconds"] == 93600
    assert body["monitored_period_days"] == 120
    assert body["disagrees_with_window"] is True
    # Authored fallback copy for the states with no date, from
    # app/providers/timing.py's own vocabulary — never a provider sentence.
    assert body["reason"] == "operator returned no date"

    for forbidden in ("detail", "phone_number", "prompt", "exception"):
        assert forbidden not in body, forbidden
    serialized = json.dumps(body)
    assert "+96279" not in serialized
    assert "fraud analyst" not in serialized
    assert "Errno" not in serialized


@pytest.mark.asyncio
async def test_an_unavailable_enrichment_round_trips_its_null_fields():
    """The absent case is the one the page has to render without inventing a
    date: nulls have to survive as nulls, not as missing keys."""
    await emit(
        {
            "type": "enrichment",
            "run_id": "run_enrich_none",
            "api": "sim-swap",
            "operation": "retrieve-date",
            "availability": "no_date",
            "provider_time": None,
            "age_seconds": None,
            "monitored_period_days": None,
            "disagrees_with_window": None,
            "reason": "operator returned no date",
            "cost": 2.0,
        }
    )
    body = run_events.events_after("run-replay-owner", "run_enrich_none", after=0)[0]["body"]
    assert body["availability"] == "no_date"
    assert body["provider_time"] is None
    assert body["age_seconds"] is None
    assert body["monitored_period_days"] is None
    assert body["disagrees_with_window"] is None


def test_a_retention_gap_is_reported_explicitly():
    result = run_events.events_after("run-replay-owner", "run_never_existed", after=5)
    assert result == []
    gap = run_events.has_gap("run-replay-owner", "run_never_existed", after=5)
    assert gap is True
