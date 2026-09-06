"""Offline, deterministic investigation runs for the judge lab (I1).

Reuses the real `Investigator`/`PolicyEngine`/`MockProvider` and the SAME
authored fixtures the console/judge page already run (`DEMO_ACTS`) — no
second decision engine, no duplicate fixture library. A run here never calls
`store.save`; it produces a `LabRun` artifact only, and is fully isolated
from the shared SSE bus via an injected per-run sink (see the Investigator
`event_sink` contract).
"""

from __future__ import annotations

import hashlib
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.agent.investigator import build_investigator
from app.agent.planner import GreedyPlanner
from app.api.routes_console import DEMO_ACTS
from app.config import settings
from app.events import _redact
from app.policy.engine import get_engine
from app.providers.mock import MockProvider
from demo.lab.models import LabRun, TraceEvent

REPO_ROOT = Path(__file__).resolve().parents[2]

# The same authored acts the console/judge page already drive, named for the
# lab rather than duplicated. Extend this mapping, never fork DEMO_ACTS.
SCENARIO_IDS: dict[str, str] = {
    "clean": "act3",
    "gap": "act5",
    "replacement": "act6",
    "ghost": "act2",
}


class UnknownScenario(ValueError):
    pass


def _fixture_digest(request) -> str:
    return hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()[:16]


def _policy_digest() -> str:
    return hashlib.sha256(Path(settings.policy_path).read_bytes()).hexdigest()[:16]


def _code_revision() -> tuple[str, bool]:
    """(revision, dirty). Best-effort: an offline generator without git access
    (a tarball export, a container with no .git) must still produce an
    artifact, just one that honestly cannot claim reproducibility."""
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
        return rev, bool(status)
    except Exception:  # noqa: BLE001 - any git failure means "cannot claim reproducibility"
        return "unknown", True


def _planner_source(events: list[TraceEvent]) -> str:
    sources = {e.selection_source for e in events if e.selection_source}
    if "llm" in sources:
        return "llm"
    if "greedy" in sources:
        return "greedy"
    return "policy"


async def run_scenario(
    scenario_id: str, *, planner=None, request_override=None, provider_override=None
) -> LabRun:
    """Run the named scenario's fixture, or `request_override` (a full
    VerificationRequest already derived from it) when a caller — I2's
    counterfactual comparator — needs one field changed while keeping the
    scenario's own digests and identity for comparison. `provider_override`
    lets I4/I9 substitute a fresh FaultInjectingProvider wrapping a fresh
    MockProvider — never a shared instance."""
    if scenario_id not in SCENARIO_IDS:
        raise UnknownScenario(scenario_id)

    run_id = "lab_" + uuid.uuid4().hex[:20]
    events: list[TraceEvent] = []
    sequence = 0

    async def sink(event: dict) -> None:
        nonlocal sequence
        event = _redact(event)
        sequence += 1
        event_type = event.get("type", "unknown")
        budget_left = event.get("budget_left")
        cost = event.get("cost")
        budget_after = (budget_left - cost) if isinstance(budget_left, (int, float)) and isinstance(
            cost, (int, float)
        ) else None
        events.append(
            TraceEvent(
                run_id=run_id,
                sequence=sequence,
                event_type=event_type,
                phase=event.get("phase", event_type),
                selection_source=event.get("planner"),
                action=event.get("action"),
                rationale=event.get("rationale"),
                budget_before=budget_left,
                budget_after=budget_after,
                evidence_step_ref=event.get("step"),
                diagnostic=event.get("diagnostic"),
                # An allow-list, not a copy of the event: `detail` is prose
                # that on the NaC path carries operator-supplied strings, and
                # this artifact is rendered on a public page.
                api=event.get("api"),
                signal=event.get("signal"),
                result=event.get("result"),
                max_age_hours=event.get("max_age_hours"),
                belief_after=event.get("p_fraud"),
            )
        )

    engine = get_engine(str(settings.policy_path))
    provider = provider_override or MockProvider()
    # The lab's offline, deterministic guarantee is constructed here, not
    # inherited from process configuration. Passing planner=None on to the
    # Investigator would reach `get_planner`, which hands back an LLMPlanner
    # whenever global settings say "llm" — so a deployment with credentials
    # configured would have this "offline" runner call a model, and I2's
    # counterfactual comparisons would be comparing two different agents.
    # An explicitly injected planner is still honoured: that is I2/I4's seam,
    # and a model-backed lab mode would come through it and be labelled.
    investigator = build_investigator(
        provider,
        engine=engine,
        planner=planner if planner is not None else GreedyPlanner(engine),
        event_sink=sink,
    )
    request = request_override or DEMO_ACTS[SCENARIO_IDS[scenario_id]].model_copy(deep=True)
    verdict = await investigator.investigate(request, run_id=run_id)

    revision, dirty = _code_revision()
    return LabRun(
        run_id=run_id,
        scenario_id=scenario_id,
        fixture_digest=_fixture_digest(request),
        policy_digest=_policy_digest(),
        code_revision=revision,
        dirty=dirty,
        generated_at=datetime.now(UTC).isoformat(),
        planner_source=_planner_source(events),
        # Stage pacing (650ms/check) is a presentation artifact added by
        # judge.html, not part of what this offline runner measures.
        timing_basis="stage_pacing",
        events=events,
        outcome={
            "decision": verdict.decision.value,
            "chain_grade": verdict.chain_grade.value if verdict.chain_grade else None,
            "confidence": verdict.confidence,
            "evidence_steps": len(verdict.chain),
            "evidence_cost": verdict.evidence_cost,
        },
        receipt_ref=None,
    )
