"""Measure how differently the LLM planner behaves from the greedy one.

This exists to answer the hardest question a judge can ask:
*"switch the LLM off — how often does greedy reach a different verdict?"* An
answer given from intuition is worth nothing; this script measures it.

It reports two different things, because they have two different answers:

A. **At one fixed decision state**, both planners are asked for the next action
   many times. This isolates the choice itself from everything downstream.
B. **Whole investigations**, run twice per scenario, comparing verdict, chain
   grade, evidence path and how many paid checks each planner spent.

Every number is reported next to the model's *answer rate*, because a planner
call that timed out and fell back is greedy answering in the model's name. It
must never be counted as agreement — that would report the system as more
deterministic than it is, in the one place a judge is most likely to probe.

    ISNAD_GEMINI_API_KEY=... .venv311/bin/python scripts/planner_divergence.py

Mock fixtures, one run, a handful of scenarios: this is a behavioural
comparison of two planners, NOT an accuracy study and NOT a latency benchmark.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import functools
import json
import os
import sys
import time
from pathlib import Path

# Same as scripts/evidence_pack.py: the documented command runs this file
# directly from the repo root, which puts scripts/ on sys.path rather than the
# root. Make that command work without requiring an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Pinned before app.config is imported, exactly as scripts/evidence_pack.py does:
# a developer's .env must not point a measurement run at a billable provider.
os.environ.setdefault("ISNAD_DATABASE_URL", "sqlite://")
os.environ["ISNAD_PROVIDER"] = "mock"
os.environ["ISNAD_DEMO_MODE"] = "true"
os.environ.setdefault("ISNAD_MERCHANT_API_KEYS", "demo-merchant-key")

from app.agent import gemini as gemini_mod
from app.agent import hypothesis as hypothesis_mod
from app.agent.investigator import build_investigator
from app.agent.planner import GreedyPlanner, LLMPlanner
from app.api.routes_console import DEMO_ACTS
from app.config import settings
from app.policy.engine import get_engine
from app.providers.mock import MockProvider

STATS: collections.Counter = collections.Counter()


def _install_retries(deadline: float, attempts: int) -> None:
    """Give the provider every chance to answer, for measurement runs only.

    The demo deliberately keeps the short fail-fast timeout from config: on
    stage a fast greedy verdict beats a slow model one. Here the opposite is
    wanted — a retry costs seconds, while a fallback silently costs the sample.
    """
    real = gemini_mod.GeminiClient._generate

    @functools.wraps(real)
    def generate(self, *args, **kwargs):
        for attempt in range(attempts):
            if time.time() > deadline:
                raise TimeoutError("benchmark deadline reached")
            try:
                out = real(self, *args, **kwargs)
                STATS["answered"] += 1
                return out
            except Exception as exc:  # noqa: BLE001 - every failure is a data point
                STATS[f"failed:{type(exc).__name__}"] += 1
                if attempt < attempts - 1:
                    time.sleep(1.0)
        raise RuntimeError("provider did not answer")

    gemini_mod.GeminiClient._generate = generate


def _verdict(request, mode: str) -> dict:
    settings.planner = mode
    verdict = asyncio.run(build_investigator(MockProvider()).investigate(request))
    return {
        "decision": str(getattr(verdict.decision, "value", verdict.decision)),
        "grade": str(getattr(verdict.chain_grade, "value", verdict.chain_grade)),
        "path": [str(getattr(link.action, "value", link.action)) for link in verdict.chain],
        "label": verdict.planner,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trials", type=int, default=12, help="samples for part A")
    ap.add_argument("--attempts", type=int, default=3, help="provider retries per call")
    ap.add_argument("--budget-seconds", type=float, default=420.0)
    ap.add_argument("--act", default="act2", help="scenario for part A")
    ap.add_argument("--json", help="write the full result here")
    args = ap.parse_args()

    if not settings.gemini_api_key:
        print("ISNAD_GEMINI_API_KEY is not set — there is nothing to compare.")
        return 2

    deadline = time.time() + args.budget_seconds
    _install_retries(deadline, args.attempts)
    engine = get_engine(str(settings.policy_path))

    print("A. ONE DECISION STATE, BOTH PLANNERS")
    request = DEMO_ACTS[args.act]
    hypothesis = hypothesis_mod.form(request.context)
    greedy, llm = GreedyPlanner(engine), LLMPlanner(engine)
    agreed = differed = unanswered = 0
    for trial in range(args.trials):
        if time.time() > deadline:
            print("   (budget reached)")
            break
        llm._calls = 0
        g = greedy.choose(hypothesis, set(), 4.0, 0.5, ())
        try:
            choice = llm.choose(hypothesis, set(), 4.0, 0.5, ())
        except Exception:  # noqa: BLE001
            choice = None
        if choice is None or choice.source != "llm":
            unanswered += 1
            print(f"   trial {trial + 1:2d}: no model answer — fell back to greedy")
            continue
        same = g.action == choice.action
        agreed += same
        differed += not same
        print(
            f"   trial {trial + 1:2d}: greedy={g.action!s:24} "
            f"llm={choice.action!s:24} {'agree' if same else 'DIFFER'}"
        )
    sampled = agreed + differed
    print(
        f"   -> answered {sampled}/{sampled + unanswered} | agreed {agreed} | differed {differed}"
    )

    print("\nB. WHOLE INVESTIGATIONS")
    rows, spend_g, spend_l = [], 0, 0
    for act, request in sorted(DEMO_ACTS.items()):
        if time.time() > deadline:
            print("   (budget reached)")
            break
        g = _verdict(request, "greedy")
        length = _verdict(request, "llm")
        rows.append({"act": act, "greedy": g, "llm": length})
        spend_g += len(g["path"])
        spend_l += len(length["path"])
        mark = (
            "**" if (g["decision"] != length["decision"] or g["grade"] != length["grade"]) else "  "
        )
        print(
            f"{mark} {act:5} greedy={g['decision']:9}/{g['grade']:17} {len(g['path'])} checks"
            f" | llm={length['decision']:9}/{length['grade']:17} {len(length['path'])} checks"
            f" | path {'same' if g['path'] == length['path'] else 'DIFFERENT'}"
            f" | label={length['label']}"
        )

    n = len(rows) or 1
    verdicts = sum(1 for r in rows if r["greedy"]["decision"] != r["llm"]["decision"])
    grades = sum(1 for r in rows if r["greedy"]["grade"] != r["llm"]["grade"])
    paths = sum(1 for r in rows if r["greedy"]["path"] != r["llm"]["path"])
    delta = (100.0 * (spend_l - spend_g) / spend_g) if spend_g else 0.0

    print("\n" + "=" * 74)
    print(f"verdict differs {verdicts}/{n} | grade differs {grades}/{n} | path differs {paths}/{n}")
    print(f"paid checks — greedy {spend_g}, llm {spend_l} ({delta:+.0f}%)")
    print(f"model: {settings.llm_model} | calls: {dict(STATS)}")
    print("Mock fixtures, one run. A planner comparison, not an accuracy study.")

    if args.json:
        payload = {
            "fixed_state": {"agreed": agreed, "differed": differed, "unanswered": unanswered},
            "investigations": rows,
            "paid_checks": {"greedy": spend_g, "llm": spend_l, "delta_pct": round(delta, 1)},
            "model": settings.llm_model,
            "calls": dict(STATS),
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
