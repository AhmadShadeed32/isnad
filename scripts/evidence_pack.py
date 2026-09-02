"""Generate a reproducible, offline evidence pack for the scripted Isnad demo.

This script deliberately forces the deterministic MockProvider and greedy
planner before importing application code. It never calls Nokia Network as Code
or a model provider. The resulting report is evidence about the local fixture
runs only; it must not be described as production traffic, operator data, or an
accuracy evaluation.

Usage:
    python scripts/evidence_pack.py
    python scripts/evidence_pack.py --output-dir /tmp/isnad-evidence
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# This is an offline artifact generator, not a switch for the live provider.
# Set before importing app.config (which reads environment settings once).
os.environ["ISNAD_PROVIDER"] = "mock"
os.environ["ISNAD_PLANNER"] = "greedy"
os.environ.setdefault("ISNAD_DATABASE_URL", "sqlite://")
# ``python scripts/evidence_pack.py`` puts scripts/, rather than the repository
# root, on sys.path. Make the documented command work without requiring install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.investigator import build_engine_for_pricing, build_investigator
from app.api.routes_console import DEMO_ACTS
from app.chain.vault import vault
from app.db import store
from app.domain.schemas import VerificationRequest
from app.policy import counterfactual
from app.providers.mock import MockProvider


@dataclass(frozen=True)
class EvidenceCase:
    """A deterministic demo fixture and the story it is intended to demonstrate."""

    identifier: str
    title: str
    purpose: str
    request: VerificationRequest


CASES: tuple[EvidenceCase, ...] = (
    EvidenceCase(
        identifier="act1_clean_signup",
        title="Act I — no-OTP clean signup",
        purpose="A clean network fact can remove unnecessary OTP friction.",
        request=DEMO_ACTS["act1"],
    ),
    EvidenceCase(
        identifier="act2_account_takeover",
        title="Act II — corroborated account-takeover risk",
        purpose="Multiple adverse network facts support stopping a high-risk COD checkout.",
        request=DEMO_ACTS["act2"],
    ),
    EvidenceCase(
        identifier="act3_thin_file",
        title="Act III — thin-file customer",
        purpose="Stable network evidence can support a low-friction decision without inventing off-network history.",
        request=DEMO_ACTS["act3"],
    ),
    EvidenceCase(
        identifier="act5_unresolved",
        title="Act V — unavailable evidence is not a decline",
        purpose="Consent withheld or an unavailable provider produces an unresolved challenge, not a false assertion.",
        request=DEMO_ACTS["act5"],
    ),
    EvidenceCase(
        identifier="act6_recent_sim_change",
        title="Act VI — recent SIM change with corroboration",
        purpose="A recent SIM change is investigated and stepped up rather than automatically declined.",
        request=DEMO_ACTS["act6"],
    ),
)


def _step_summary(link: Any, engine: Any) -> dict[str, Any]:
    return {
        "step": link.step,
        "action": link.action.value,
        "api": link.api,
        "result": link.result.value,
        "signal": link.signal,
        "source": link.source,
        # MockProvider encodes this fixture timing in the link; it is useful for
        # explaining the scripted sequence, but it is not a network measurement.
        "scripted_provider_latency_ms": link.latency_ms,
        "policy_cost_units": engine.action_cost(link.action),
    }


async def run_case(case: EvidenceCase) -> dict[str, Any]:
    """Run a fixture through the local agent, store it, and verify its signature."""
    investigator = build_investigator(MockProvider())
    engine = build_engine_for_pricing()
    verdict = await investigator.investigate(case.request)
    request_hash = hashlib.sha256(case.request.model_dump_json().encode("utf-8")).hexdigest()
    record = await store.save_async(
        verdict, subject=case.request.phone_number, request_hash=request_hash
    )
    signature_valid = vault.verify_with(
        record.public_key, record.verdict_json.encode("utf-8"), record.signature
    )
    alternative = counterfactual.compute(verdict, case.request.phone_number, engine)

    return {
        "scenario": {
            "id": case.identifier,
            "title": case.title,
            "purpose": case.purpose,
            "fixture": "deterministic MockProvider; no Nokia Network as Code or model-provider call was made",
        },
        "outcome": {
            "decision": verdict.decision.value,
            "chain_grade": verdict.chain_grade.value if verdict.chain_grade else None,
            "confidence": verdict.confidence,
            "hypothesis": verdict.hypothesis,
            "reason": verdict.reason,
        },
        "orchestration": {
            "planner": verdict.planner,
            "provider_sources": verdict.provider_sources,
            "evidence_steps": len(verdict.chain),
            "evidence_cost_units": verdict.evidence_cost,
            "wall_clock_latency_ms": verdict.latency_ms,
        },
        "evidence": [_step_summary(link, engine) for link in verdict.chain],
        "signed_chain_verification": {
            "valid": signature_valid,
            "key_trusted": vault.trusts(record.public_key),
            "algorithm": "Ed25519",
            "signed_at": record.signed_at,
        },
        "counterfactual": alternative.model_dump(mode="json") if alternative else None,
    }


async def build_report(cases: Iterable[EvidenceCase] = CASES) -> dict[str, Any]:
    """Return a JSON-serializable report. Kept separate for focused tests."""
    scenario_reports = [await run_case(case) for case in cases]
    return {
        "report_type": "isnad_local_scripted_evidence_pack",
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": {
            "provider": "mock",
            "planner": "greedy",
            "network_calls": False,
            "model_provider_calls": False,
            "claim": (
                "This report documents deterministic local fixtures. It is not "
                "an accuracy study, a production-traffic report, or proof of "
                "operator availability."
            ),
        },
        "scenarios": scenario_reports,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render the reviewable companion to the machine-readable JSON report."""
    scope = report["scope"]
    lines = [
        "# Isnad local scripted evidence pack",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        (
            "> **Scope.** This is a deterministic local MockProvider run. It made no Nokia "
            "Network as Code or model-provider calls. It is not an accuracy study, production "
            "traffic report, proof of operator availability, or latency benchmark."
        ),
        "",
        f"- Provider: `{scope['provider']}`",
        f"- Planner: `{scope['planner']}`",
        "- Signed-chain check: Ed25519 signature recomputed over the stored verdict JSON",
        "",
        "## Scenario summary",
        "",
        "| Scenario | Outcome | Planner | Source(s) | Steps | Cost units | Local wall clock | Signature |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for item in report["scenarios"]:
        scenario = item["scenario"]
        outcome = item["outcome"]
        orchestration = item["orchestration"]
        signature = item["signed_chain_verification"]
        outcome_label = f"{outcome['decision']} / {outcome['chain_grade']}"
        sources = ", ".join(orchestration["provider_sources"]) or "none"
        lines.append(
            "| {title} | {outcome} | {planner} | {sources} | {steps} | {cost:.2f} | "
            "{latency} ms | {verified} |".format(
                title=scenario["title"],
                outcome=outcome_label,
                planner=orchestration["planner"],
                sources=sources,
                steps=orchestration["evidence_steps"],
                cost=orchestration["evidence_cost_units"],
                latency=orchestration["wall_clock_latency_ms"],
                verified="valid" if signature["valid"] and signature["key_trusted"] else "FAILED",
            )
        )

    for item in report["scenarios"]:
        scenario = item["scenario"]
        outcome = item["outcome"]
        verification = item["signed_chain_verification"]
        lines.extend(
            [
                "",
                f"## {scenario['title']}",
                "",
                scenario["purpose"],
                "",
                (
                    f"Outcome: **{outcome['decision']}** · chain grade: "
                    f"**{outcome['chain_grade']}** · planner: `{item['orchestration']['planner']}`."
                ),
                "",
                "| # | API | Result | Signal | Source | Policy cost | Scripted fixture latency |",
                "| ---: | --- | --- | --- | --- | ---: | ---: |",
            ]
        )
        for step in item["evidence"]:
            lines.append(
                "| {step} | {api} | {result} | `{signal}` | {source} | {cost:.2f} | "
                "{latency} ms |".format(
                    step=step["step"],
                    api=step["api"],
                    result=step["result"],
                    signal=step["signal"],
                    source=step["source"],
                    cost=step["policy_cost_units"],
                    latency=step["scripted_provider_latency_ms"],
                )
            )
        lines.extend(
            [
                "",
                (
                    "Signed-chain verification: "
                    f"`valid={verification['valid']}` · "
                    f"`key_trusted={verification['key_trusted']}` · "
                    f"`algorithm={verification['algorithm']}`."
                ),
                "",
                (
                    "Counterfactual figures, if present in the JSON report, retain their own "
                    "basis and source. Unpriced fields are intentionally null rather than guessed."
                ),
            ]
        )
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "evidence-pack.json"
    markdown_path = output_dir / "evidence-pack.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".isnad/evidence-pack"),
        help="Directory for evidence-pack.json and evidence-pack.md (default: .isnad/evidence-pack)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = asyncio.run(build_report())
    json_path, markdown_path = write_report(report, args.output_dir)
    print(f"Wrote local scripted evidence pack: {json_path}")
    print(f"Wrote reviewable companion: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
