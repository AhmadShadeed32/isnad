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
from app.judge import evidence as judge_evidence
from app.policy.engine import get_engine
from app.providers import nac_contract
from app.providers.mock import MockProvider

STATS: collections.Counter = collections.Counter()

# Two cohorts, never averaged together.
#
#   nokia_paired — the two documented simulator subscribers, answered by the
#                  Nokia-contract transport through the real SDK. Only the two
#                  swap checks are available, which is what the judge demo
#                  exposes.
#   custom_mock  — the authored console stories. Richer, more actions, and NOT
#                  Nokia contracts. Useful, and a different question.
#
# Mixing them would publish one divergence rate over two different action sets.
COHORTS = ("nokia_paired", "custom_mock")


def _forbid_hosted_transport() -> None:
    """A measurement run must not be able to reach an operator, ever.

    `ISNAD_PROVIDER=mock` is pinned above, but the judge path builds its own
    provider and does not consult that setting. This closes the remaining door:
    if anything in this script ever tries to build the hosted client, the run
    fails loudly instead of quietly billing someone.
    """

    def refuse(*_args, **_kwargs):
        raise RuntimeError(
            "planner_divergence must never open a hosted Nokia transport; "
            "this is a local measurement run"
        )

    nac_contract.build_hosted_client = refuse


def _install_retries(deadline: float, attempts: int, max_requests: int) -> None:
    """Give the provider every chance to answer, for measurement runs only.

    The demo deliberately keeps the short fail-fast timeout from config: on
    stage a fast greedy verdict beats a slow model one. Here the opposite is
    wanted — a retry costs seconds, while a fallback silently costs the sample.

    `max_requests` is a HARD CEILING on billable requests across the whole run,
    counting retries. The deadline alone did not bound spend: a fast-failing
    endpoint retries as often as the clock allows, and `--attempts` multiplies
    every sample by itself. Once the ceiling is reached the run stops asking
    and every remaining sample is reported as unanswered — which is a true
    statement about the measurement, where a silent extra bill is not.
    """
    real = gemini_mod.GeminiClient._generate

    @functools.wraps(real)
    def generate(self, *args, **kwargs):
        for attempt in range(attempts):
            if time.time() > deadline:
                raise TimeoutError("benchmark deadline reached")
            if STATS["requests"] >= max_requests:
                STATS["skipped:request_ceiling"] += 1
                raise RuntimeError(f"request ceiling reached ({max_requests})")
            STATS["requests"] += 1
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


def _paired_verdict(scenario: str, mode: str, engine) -> dict:
    """One paired-cohort investigation, with everything else held identical.

    Same request context, same available actions, same policy, same operation
    budget, same enrichment setting (off), and a provider instance built fresh
    per trial so no cache, transport or attempt log is shared between the two
    planners. The only difference is which planner is asked.
    """
    ctx = judge_evidence.RunContext(
        source=judge_evidence.EvidenceSource.MOCK_NOKIA,
        scenario=scenario,
        contract_version=nac_contract.contract_version(),
        planner=(
            judge_evidence.JudgePlanner.GREEDY
            if mode == "greedy"
            else judge_evidence.JudgePlanner.GEMINI
        ),
        policy_digest=judge_evidence.policy_digest(),
        run_id="",
        owner="planner-divergence",
    )
    provider, log = judge_evidence.build_provider(ctx)
    planner = GreedyPlanner(engine) if mode == "greedy" else LLMPlanner(engine)
    verdict = asyncio.run(
        build_investigator(provider, planner=planner).investigate(
            judge_evidence.request_for(scenario),
            available_actions=set(judge_evidence.PAIRED_ACTIONS),
        )
    )
    row = _row_for(verdict)
    # The transport's own count, not the chain's length: they are different
    # numbers and only one of them is an API call.
    row["transport_attempts"] = log.count
    return row


def _row_for(verdict) -> dict:
    return {
        "decision": str(getattr(verdict.decision, "value", verdict.decision)),
        "grade": str(getattr(verdict.chain_grade, "value", verdict.chain_grade)),
        "path": [str(getattr(link.action, "value", link.action)) for link in verdict.chain],
        "label": verdict.planner,
        # Three different quantities that were previously all reported as
        # "paid checks" by counting `path`:
        #   links      — how many rows are in the chain. Includes free local
        #                evidence, and counts a check and its separately
        #                priced date call as one.
        #   operations — billable provider operations actually attempted.
        #   cost       — spend in the policy's own budget units.
        # `len(path)` is none of them, and was the number the comparison
        # published.
        "links": len(verdict.chain),
        "operations": verdict.operations,
        "cost": verdict.evidence_cost,
        "stop": verdict.stopping_reason,
    }


def _verdict(request, mode: str) -> dict:
    settings.planner = mode
    verdict = asyncio.run(build_investigator(MockProvider()).investigate(request))
    row = _row_for(verdict)
    # The legacy cohort runs the authored MockProvider, which never opens a
    # transport at all.
    row["transport_attempts"] = 0
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trials", type=int, default=12, help="samples for part A")
    ap.add_argument("--attempts", type=int, default=3, help="provider retries per call")
    ap.add_argument("--budget-seconds", type=float, default=420.0)
    ap.add_argument(
        "--max-requests",
        type=int,
        default=60,
        help="hard ceiling on billable model requests for the whole run, retries included",
    )
    ap.add_argument("--act", default="act2", help="scenario for part A")
    ap.add_argument(
        "--cohort",
        choices=[*COHORTS, "all"],
        default="all",
        help="which scenario cohort to run in part B; they are never averaged together",
    )
    ap.add_argument("--json", help="write the full result here")
    args = ap.parse_args()

    _forbid_hosted_transport()

    if not settings.gemini_api_key:
        print("ISNAD_GEMINI_API_KEY is not set — there is nothing to compare.")
        return 2

    deadline = time.time() + args.budget_seconds
    _install_retries(deadline, args.attempts, args.max_requests)
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

    cohorts: dict[str, dict] = {}

    if args.cohort in ("nokia_paired", "all"):
        print("\nB1. WHOLE INVESTIGATIONS — nokia_paired cohort")
        print("    Nokia-contract fixtures, two swap checks available, no date enrichment.")
        paired_rows = []
        for scenario in sorted(nac_contract.paired_scenarios()):
            if time.time() > deadline:
                print("   (budget reached)")
                break
            g = _paired_verdict(scenario, "greedy", engine)
            length = _paired_verdict(scenario, "llm", engine)
            paired_rows.append({"scenario": scenario, "greedy": g, "llm": length})
            mark = (
                "**"
                if (g["decision"] != length["decision"] or g["grade"] != length["grade"])
                else "  "
            )
            print(
                f"{mark} {scenario:20} greedy={g['decision']:9}/{g['grade']:17}"
                f" {g['operations']} ops/{g['transport_attempts']} attempts"
                f" | llm={length['decision']:9}/{length['grade']:17}"
                f" {length['operations']} ops/{length['transport_attempts']} attempts"
                f" | path {'same' if g['path'] == length['path'] else 'DIFFERENT'}"
                f" | label={length['label']}"
            )
        cohorts["nokia_paired"] = {
            "rows": paired_rows,
            "verdict_differs": sum(
                1 for r in paired_rows if r["greedy"]["decision"] != r["llm"]["decision"]
            ),
            "grade_differs": sum(
                1 for r in paired_rows if r["greedy"]["grade"] != r["llm"]["grade"]
            ),
            "path_differs": sum(1 for r in paired_rows if r["greedy"]["path"] != r["llm"]["path"]),
            "trials": len(paired_rows),
            "genuine_llm_labels": sum(1 for r in paired_rows if r["llm"]["label"] == "llm"),
        }

    acts = DEMO_ACTS if args.cohort in ("custom_mock", "all") else {}
    if acts:
        print(
            "\nB2. WHOLE INVESTIGATIONS — custom_mock cohort"
            " (authored stories, not Nokia contracts)"
        )
    rows = []
    cost_g = cost_l = 0.0
    ops_g = ops_l = 0
    for act, request in sorted(acts.items()):
        if time.time() > deadline:
            print("   (budget reached)")
            break
        g = _verdict(request, "greedy")
        length = _verdict(request, "llm")
        rows.append({"act": act, "greedy": g, "llm": length})
        cost_g += g["cost"]
        cost_l += length["cost"]
        ops_g += g["operations"]
        ops_l += length["operations"]
        mark = (
            "**" if (g["decision"] != length["decision"] or g["grade"] != length["grade"]) else "  "
        )
        print(
            f"{mark} {act:5} greedy={g['decision']:9}/{g['grade']:17}"
            f" {g['operations']} ops/{g['cost']:g} units"
            f" | llm={length['decision']:9}/{length['grade']:17}"
            f" {length['operations']} ops/{length['cost']:g} units"
            f" | path {'same' if g['path'] == length['path'] else 'DIFFERENT'}"
            f" | label={length['label']}"
        )

    verdicts = sum(1 for r in rows if r["greedy"]["decision"] != r["llm"]["decision"])
    grades = sum(1 for r in rows if r["greedy"]["grade"] != r["llm"]["grade"])
    paths = sum(1 for r in rows if r["greedy"]["path"] != r["llm"]["path"])
    delta = (100.0 * (cost_l - cost_g) / cost_g) if cost_g else 0.0

    print("\n" + "=" * 74)
    # Per cohort, with its own denominator. One rate over two different action
    # sets would be a number nobody could reproduce or interpret.
    paired = cohorts.get("nokia_paired")
    if paired:
        trials = paired["trials"]
        print(
            f"nokia_paired  ({trials} scenarios): verdict differs {paired['verdict_differs']}"
            f"/{trials} | grade differs {paired['grade_differs']}/{trials}"
            f" | path differs {paired['path_differs']}/{trials}"
            f" | genuine llm labels {paired['genuine_llm_labels']}/{trials}"
        )
    if rows:
        n = len(rows)
        print(
            f"custom_mock   ({n} scenarios): verdict differs {verdicts}/{n}"
            f" | grade differs {grades}/{n} | path differs {paths}/{n}"
        )
        print(
            f"billable operations — greedy {ops_g}, llm {ops_l}"
            f" | evidence cost (budget units) — greedy {cost_g:g}, llm {cost_l:g} ({delta:+.0f}%)"
        )
    print(f"model: {settings.llm_model} | requests: {dict(STATS)} | ceiling {args.max_requests}")
    print("Mock fixtures, one run. A planner comparison, not an accuracy study.")

    if args.json:
        import subprocess

        try:
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            ).stdout.strip()
            dirty = bool(
                subprocess.run(
                    ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
                ).stdout.strip()
            )
        except Exception:  # noqa: BLE001 - identity is best-effort, never fatal
            revision, dirty = "unknown", True
        payload = {
            # Identity, so a number in a report can be traced to what produced
            # it. A comparison whose inputs cannot be named is an anecdote.
            "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "revision": revision,
            "working_tree_dirty": dirty,
            "contract_version": nac_contract.contract_version(),
            "policy_digest": judge_evidence.policy_digest(),
            "model": settings.llm_model,
            "command": " ".join(sys.argv),
            "cohorts_note": (
                "nokia_paired and custom_mock are separate cohorts with different "
                "available actions. They are never averaged together."
            ),
            "fixed_state": {
                "act": args.act,
                "agreed": agreed,
                "differed": differed,
                "unanswered": unanswered,
                "trials_scheduled": args.trials,
            },
            "cohorts": cohorts,
            "investigations": rows,
            "operations": {"greedy": ops_g, "llm": ops_l},
            "evidence_cost": {
                "greedy": round(cost_g, 2),
                "llm": round(cost_l, 2),
                "delta_pct": round(delta, 1),
            },
            "calls": dict(STATS),
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
