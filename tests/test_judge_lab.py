"""I1's shared runner: deterministic, isolated, offline investigation replays.

No live network/model call, no mutation of process-global settings or the
shared SSE bus, and no effect whatsoever on the signed Verdict path.
"""

from __future__ import annotations

import asyncio

import pytest

from demo.lab.runner import UnknownScenario, run_scenario


@pytest.mark.asyncio
async def test_an_unknown_scenario_id_is_rejected():
    with pytest.raises(UnknownScenario):
        await run_scenario("not-a-real-scenario")


@pytest.mark.asyncio
async def test_a_scenario_run_is_deterministic():
    """Same scenario, same fixed fixture and greedy planner -> the same
    sequence of decisions and outcome, run to run."""
    first = await run_scenario("replacement")
    second = await run_scenario("replacement")

    def stable(run):
        return [
            (e.event_type, e.phase, e.selection_source, e.action, e.rationale)
            for e in run.events
        ]

    assert stable(first) == stable(second)
    assert first.outcome == second.outcome
    assert first.fixture_digest == second.fixture_digest
    assert first.policy_digest == second.policy_digest
    assert first.run_id != second.run_id  # each run still gets its own identity


@pytest.mark.asyncio
async def test_concurrent_runs_do_not_leak_events_into_each_other():
    replacement, clean = await asyncio.gather(run_scenario("replacement"), run_scenario("clean"))
    assert all(e.run_id == replacement.run_id for e in replacement.events)
    assert all(e.run_id == clean.run_id for e in clean.events)
    assert replacement.outcome != clean.outcome


@pytest.mark.asyncio
async def test_a_run_never_persists_a_chain():
    from app.db.database import SessionLocal
    from app.db.models import ChainRow

    before = None
    with SessionLocal() as session:
        before = session.query(ChainRow).count()

    await run_scenario("gap")

    with SessionLocal() as session:
        after = session.query(ChainRow).count()
    assert after == before, "a lab run must never call store.save"


@pytest.mark.asyncio
async def test_every_run_has_a_named_planner_source():
    run = await run_scenario("clean")
    assert run.planner_source in {"llm", "greedy", "policy"}
    assert run.events, "a run with no events cannot be reconciled with any evidence"


@pytest.mark.asyncio
async def test_to_dict_round_trips_without_dataclass_leakage():
    run = await run_scenario("clean")
    payload = run.to_dict()
    assert payload["schema_version"] == 1
    assert isinstance(payload["events"], list)
    assert all(isinstance(e, dict) for e in payload["events"])
