"""Build the versioned artifact bundle the /lab page serves (I1/I2/I3/I4/I9).

The lab page renders *recordings*. It does not run an investigation, and
there is no endpoint behind it that will: every case a judge can select was
run here, offline, against a fixed authored fixture, and the page replays
what was recorded. That is what makes "replay controls scrub the recorded
timeline without resending requests" (I1 step 4) and "cannot incur additional
model spend" true by construction rather than by promise.

Everything is produced through the shared `demo/lab` runner, which pins its
own MockProvider and GreedyPlanner (see the handoff's F3) — so this bundle is
identical whatever the surrounding deployment is configured for.

    .venv311/bin/python scripts/build_lab_artifacts.py

Writes demo/lab/artifacts/bundle.json, which is committed. A committed
recording goes stale the moment the policy or the code moves, so the bundle
records the fixture, policy and code identity it ran under and the page
reports any drift from what is running now rather than hiding it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# In-memory only: importing the app creates tables, and this generator has no
# business touching a real database.
os.environ.setdefault("ISNAD_DATABASE_URL", "sqlite://")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUT = REPO_ROOT / "demo" / "lab" / "artifacts" / "bundle.json"

BUNDLE_SCHEMA_VERSION = 1

# Stated up front, because I9 step 2 requires the assumptions to be visible
# *before* the case runs: a surprise that turns out to be a hidden policy
# change is not a challenge, it is a trick.
LIMITS = [
    (
        "Every case here is an authored synthetic fixture. Authored data is not "
        "independent ground truth, and a case that did not appear in the lead "
        "recording is still not a statistically held-out test."
    ),
    (
        "These are recordings, not live runs. Selecting a case replays what this "
        "generator captured; nothing on the page calls a provider or a model."
    ),
    (
        "The same policy file and the same deterministic greedy planner ran every "
        "case. Nothing was tuned per case."
    ),
    (
        "Timings are not measured. The 650ms pacing in the judge demo is a "
        "presentation choice; these recordings carry ordering, not duration."
    ),
    (
        "Counterfactual branches are unsigned hypothetical fixtures. They are not "
        "merchant decisions, and no real-world change follows from one."
    ),
]


async def _build_cases() -> list[dict]:
    from demo.lab.challenge import CASES, run_case

    cases = []
    for case_id, case in CASES.items():
        run = await run_case(case_id)
        cases.append(
            {
                "case_id": case_id,
                "description": case["description"],
                "scenario_id": case["scenario_id"],
                # The two ways a case departs from its base scenario, named
                # rather than left for the reader to infer from the trace.
                "fault_profile": case.get("fault_profile"),
                "removes_claimed_location": bool(case.get("remove_claimed_location")),
                "run": run.to_dict(),
            }
        )
    return cases


async def _build_comparison() -> dict | None:
    """I2's one-fact counterfactual. `None` when the base scenario has no
    claimed location to remove — an absent comparison says so; it does not
    quietly substitute a different change."""
    from demo.lab.compare import NoClaimedLocation, compare_missing_location_claim

    try:
        comparison = await compare_missing_location_claim("replacement")
    except NoClaimedLocation:
        return None
    return comparison.to_dict()


async def build_bundle() -> dict:
    from demo.lab.challenge import seeded_order
    from demo.lab.runner import _code_revision, _policy_digest

    build_evidence_comparison = _load_generator("build_evidence_comparison.py")

    # The codebase's own definition of "the network did not answer", exported
    # rather than restated in the page's JavaScript: a second copy of this set
    # would drift, and the difference between a hole in the chain and an
    # adverse finding is exactly what the page must not get wrong.
    from app.agent.investigator import _UNRESOLVED_SIGNALS

    revision, dirty = _code_revision()
    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "unresolved_signals": sorted(_UNRESOLVED_SIGNALS),
        "generated_at": datetime.now(UTC).isoformat(),
        "code_revision": revision,
        "dirty": dirty,
        "policy_digest": _policy_digest(),
        "cases": await _build_cases(),
        # A fixed seed, recorded, so "shuffled" is reproducible rather than a
        # different order every time a judge reloads (I9 step 5).
        "shuffle_seed": 20260906,
        "shuffled_order": seeded_order(20260906),
        "comparison": await _build_comparison(),
        "evidence_report": await build_evidence_comparison.build_report(),
        "limits": LIMITS,
    }


def _load_generator(filename: str):
    import importlib.util

    path = REPO_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    bundle = asyncio.run(build_bundle())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote {args.out}")
    for case in bundle["cases"]:
        outcome = case["run"]["outcome"]
        print(f"  {case['case_id']}: {outcome['decision']} / {outcome['chain_grade']}")
    if bundle["dirty"]:
        print("  NOTE: built from a dirty working tree; the bundle cannot claim reproducibility")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
