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
    from demo.lab.models import SCHEMA_VERSION

    run = await run_scenario("clean")
    payload = run.to_dict()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert isinstance(payload["events"], list)
    assert all(isinstance(e, dict) for e in payload["events"])


@pytest.mark.asyncio
async def test_an_evidence_event_records_what_the_network_answered():
    """Schema 2. Without the answer, a trace row says only "evidence link #3"
    and I1's acceptance — an auditor reconciling every check with its evidence
    link — has nothing to reconcile against."""
    run = await run_scenario("replacement")
    evidence = [e for e in run.events if e.event_type == "evidence"]
    assert evidence
    for event in evidence:
        assert event.api
        assert event.signal
        assert event.result in {"PASS", "FLAG", "INFO"}


@pytest.mark.asyncio
async def test_a_recorded_event_never_carries_provider_prose():
    """`detail` on the NaC path is operator-supplied text, and these artifacts
    are rendered on a public page. The capture is an allow-list, not a copy."""
    run = await run_scenario("replacement")
    for event in run.events:
        assert "detail" not in event.to_dict()
        assert "source" not in event.to_dict()


# --- F3: the offline guarantee, under a live LLM configuration ----------------
#
# `run_scenario` passed planner=None straight through, so `Investigator` fell
# back to `get_planner`, which returns an LLMPlanner whenever global settings
# say "llm". The CLI's `os.environ.setdefault("ISNAD_PLANNER", "greedy")` does
# not help: setdefault yields to an environment that already asks for llm, and
# settings are read once at import. A deployment with credentials configured
# could therefore have the "fully offline, deterministic" lab call a model —
# and every test here pinned settings to greedy, which hid it.


@pytest.fixture
def _configured_for_llm(monkeypatch):
    """Global config asking for the model, with a credential present."""
    from app.config import settings

    monkeypatch.setattr(settings, "planner", "llm")
    monkeypatch.setattr(settings, "gemini_api_key", "not-a-real-key-but-configured")
    return settings


@pytest.mark.asyncio
async def test_the_lab_runner_stays_greedy_when_global_settings_say_llm(
    _configured_for_llm, monkeypatch
):
    """The offline guarantee is the lab's whole claim: its comparisons are only
    meaningful if the same inputs give the same run. It cannot be delegated to
    ambient configuration."""
    import app.agent.planner as planner_module

    def _exploded(*args, **kwargs):  # pragma: no cover - the point is it is not called
        raise AssertionError("the offline lab reached the model planner")

    monkeypatch.setattr(planner_module.LLMPlanner, "__init__", _exploded)
    monkeypatch.setattr(planner_module.LLMPlanner, "_maybe_client", staticmethod(_exploded))

    run = await run_scenario("replacement")
    assert run.planner_source == "greedy"
    assert run.events


@pytest.mark.asyncio
async def test_the_lab_runner_does_not_consult_the_ambient_planner_factory(
    _configured_for_llm, monkeypatch
):
    """Not "it happens to return greedy today" — the lab must not ask."""
    import app.agent.investigator as investigator_module

    def _exploded(*args, **kwargs):  # pragma: no cover
        raise AssertionError("the offline lab consulted get_planner")

    monkeypatch.setattr(investigator_module, "get_planner", _exploded)

    run = await run_scenario("clean")
    assert run.planner_source == "greedy"


@pytest.mark.asyncio
async def test_the_lab_runner_still_honours_an_explicitly_injected_planner(
    _configured_for_llm,
):
    """Pinning the default must not take away the injection point I2/I4 use."""
    from app.agent.planner import GreedyPlanner
    from app.config import settings
    from app.policy.engine import get_engine

    class LabelledPlanner(GreedyPlanner):
        source = "llm"  # a deliberately different label, to prove it survives

    engine = get_engine(str(settings.policy_path))
    run = await run_scenario("clean", planner=LabelledPlanner(engine))
    assert run.planner_source == "llm"


@pytest.mark.asyncio
async def test_the_lab_runner_does_not_mutate_global_settings(_configured_for_llm):
    """F3 step 2: isolation by construction, not by reaching into the process
    every other request is reading from."""
    from app.config import settings

    await run_scenario("gap")
    assert settings.planner == "llm"


def test_the_generators_do_not_claim_an_environment_variable_as_the_guarantee():
    """`setdefault` yields to an environment that already asks for llm, so it
    never was one. The guarantee lives in the runner's own construction."""
    from pathlib import Path

    for name in ("build_judge_lab.py", "build_evidence_comparison.py"):
        source = (Path(__file__).resolve().parents[1] / "scripts" / name).read_text(encoding="utf-8")
        assert 'setdefault("ISNAD_PLANNER"' not in source, name
        assert 'setdefault("ISNAD_PROVIDER"' not in source, name
