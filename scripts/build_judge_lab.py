"""Build LabRun artifacts for every judge-lab scenario (I1).

Fully offline: mock provider, greedy planner, no network/model call, no
signed chain persisted. Each artifact records the exact fixture and policy
digests and the code revision it ran against, so it can be independently
reproduced or shown to be stale.

    .venv311/bin/python scripts/build_judge_lab.py --out /tmp/isnad-judge-lab
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("ISNAD_DATABASE_URL", "sqlite://")
os.environ.setdefault("ISNAD_PROVIDER", "mock")
os.environ.setdefault("ISNAD_PLANNER", "greedy")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


async def _build_all() -> list[dict]:
    from demo.lab.runner import SCENARIO_IDS, run_scenario

    runs = []
    for scenario_id in SCENARIO_IDS:
        run = await run_scenario(scenario_id)
        runs.append(run.to_dict())
    return runs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=Path("/tmp/isnad-judge-lab"))
    args = parser.parse_args()

    runs = asyncio.run(_build_all())

    args.out.mkdir(parents=True, exist_ok=True)
    for run in runs:
        path = args.out / f"{run['scenario_id']}.json"
        path.write_text(json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        path.chmod(0o600)
        print(f"wrote {path} — {run['outcome']['decision']} / {run['outcome']['chain_grade']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
