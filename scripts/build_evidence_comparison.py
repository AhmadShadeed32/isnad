"""I3 — evidence budget and decision comparison, combined into one report.

Reuses `independent_evaluation.py` (authored dataset, three methods on
identical evidence) and `false_decline_baseline.py` (generated ADVERSE-1/
UNKNOWN-1/FRAUD population against two rule-based baselines) exactly as they
already exist — loaded as modules, not reimplemented, and each one's own
isolation/leakage guards stay in force. This script only combines their
already-produced JSON with dataset/policy/code digests; it computes nothing
about the decision itself.

Every count below is a raw denominator, not an accuracy claim: synthetic
expectation agreement is not production accuracy, and a lower call count
alone is not proof that AI helped.

    .venv311/bin/python scripts/build_evidence_comparison.py --out /tmp/isnad-evidence-comparison.json
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# In-memory only: importing the app creates tables, and this generator has no
# business touching a real database.
os.environ.setdefault("ISNAD_DATABASE_URL", "sqlite://")
# The provider and planner are NOT set here. setdefault yields to an
# environment that already asks for `llm`, so an environment variable was never
# the offline guarantee it looked like; demo/lab/runner.py constructs a
# MockProvider and a GreedyPlanner itself, whatever this process is configured
# for (see the handoff's F3).

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _code_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=5, check=True
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - a missing git tree cannot claim a revision
        return "unknown"


def _policy_digest() -> str:
    from app.config import settings

    return hashlib.sha256(Path(settings.policy_path).read_bytes()).hexdigest()[:16]


async def build_report() -> dict:
    independent_evaluation = _load("independent_evaluation", REPO_ROOT / "scripts" / "independent_evaluation.py")
    false_decline_baseline = _load("false_decline_baseline", REPO_ROOT / "scripts" / "false_decline_baseline.py")

    dataset = independent_evaluation.load_dataset()
    dataset_digest = hashlib.sha256(independent_evaluation.FIXTURE_PATH.read_bytes()).hexdigest()[:16]
    ie_report = await independent_evaluation.evaluate(dataset)

    from app.config import settings
    from app.policy.engine import get_engine

    engine = get_engine(str(settings.policy_path))
    fdb_rows = await false_decline_baseline.run(
        false_decline_baseline.population(engine.cfg.get("signals", {})), engine
    )
    innocent = [r for r in fdb_rows if not r["deserves_decline"]]
    guilty = [r for r in fdb_rows if r["deserves_decline"]]

    def declines(rows, key=None):
        return sum(1 for r in rows if (r["baseline"][key] if key else r["isnad"]).value == "DECLINE")

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "code_revision": _code_revision(),
        "policy_digest": _policy_digest(),
        "independent_evaluation": {
            "dataset_digest": dataset_digest,
            "case_count": len(dataset.cases) if hasattr(dataset, "cases") else None,
            "methods": ie_report["methods"],
            "pairwise_disagreements": ie_report["pairwise_disagreements"],
        },
        "false_decline_baseline": {
            "case_count": len(fdb_rows),
            "innocent_denominator": len(innocent),
            "guilty_denominator": len(guilty),
            "false_declines": {
                "isnad": declines(innocent),
                "single-signal": declines(innocent, "single-signal"),
                "collapse-unknowns": declines(innocent, "collapse-unknowns"),
            },
            "missed_fraud": {
                "isnad": sum(1 for r in guilty if r["isnad"].value == "ALLOW"),
                "single-signal": sum(1 for r in guilty if r["baseline"]["single-signal"].value == "ALLOW"),
                "collapse-unknowns": sum(
                    1 for r in guilty if r["baseline"]["collapse-unknowns"].value == "ALLOW"
                ),
            },
        },
        "limits": [
            "Both source evaluations are scripted, synthetic fixtures, not production traffic.",
            "Synthetic expectation agreement is not production accuracy.",
            "A lower call count alone is not proof that AI helped -- see each source's own denominator.",
            "Every USD/cost figure, if displayed elsewhere, is a configured unit, not a contracted price.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=Path("/tmp/isnad-evidence-comparison.json"))
    args = parser.parse_args()

    report = asyncio.run(build_report())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out.chmod(0o600)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
