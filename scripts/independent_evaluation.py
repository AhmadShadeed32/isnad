"""Run a fixed, synthetic safety evaluation against Isnad and two comparators.

The fixture is authored separately from ``policy.yaml`` and is never generated
from the implementation's signal table. Its labels are review expectations for
specific synthetic situations. They are not production ground truth, a fraud
prevalence sample, or independent real-world validation.

All three methods receive the same prescribed evidence. ``isnad-greedy`` runs
the real sequential investigator. ``corroboration-aware-rules`` runs all served
checks and requires adverse evidence from two independence groups to decline.
``full-evidence-same-policy`` applies Isnad's prior, weights, and thresholds to
all served checks, exposing the effect of early stopping separately from policy.

The report deliberately uses counts: authored-expectation disagreements,
CHALLENGE frequency, execution errors, and evidence calls. It does not call the
result accuracy because the fixture is synthetic and its labels are judgments.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from statistics import mean

# Pin the offline path before importing any application module. Assignment is
# deliberate: a developer's .env or shell must never turn this evaluator into a
# model request, a billable CAMARA call, or a credential-bearing process.
os.environ["ISNAD_DATABASE_URL"] = "sqlite://"
os.environ["ISNAD_PROVIDER"] = "mock"
os.environ["ISNAD_PLANNER"] = "greedy"
os.environ["ISNAD_GEMINI_API_KEY"] = ""
os.environ["ISNAD_NAC_API_KEY"] = ""
os.environ["ISNAD_NAC_CLIENT_ID"] = ""
os.environ["ISNAD_NAC_CLIENT_SECRET"] = ""
os.environ["ISNAD_MERCHANT_API_KEYS"] = ""

ROOT = Path(__file__).resolve().parents[1]
os.environ["ISNAD_POLICY_PATH"] = str(ROOT / "app/policy/policy.yaml")
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.agent.investigator import build_investigator
from app.domain.enums import Action, Decision, Result
from app.domain.schemas import RequestContext, VerificationRequest
from app.policy.engine import PolicyEngine, logodds_to_p
from app.providers.mock import MockProvider

FIXTURE_PATH = ROOT / "tests" / "fixtures" / "independent_evaluation.json"

# These are the provider-backed actions the current investigator can buy. Device
# Intelligence and OTP are intentionally absent because no provider serves them;
# local registry actions are outside the forward-verification fixture.
SERVABLE_ACTIONS = (
    Action.NUMBER_VERIFY,
    Action.SIM_SWAP,
    Action.DEVICE_SWAP,
    Action.LOCATION_VERIFY,
    Action.REACHABILITY,
    Action.ROAMING,
)

# INFO is not automatically unresolved: ROAMING_NETWORK is an answer. These
# values specifically mean the requested fact could not be determined.
UNRESOLVED_SIGNALS = {
    "CONSENT_REQUIRED",
    "PROVIDER_UNAVAILABLE",
    "EVIDENCE_UNAVAILABLE",
    "LOCATION_UNKNOWN",
    "LOCATION_PARTIAL",
}


class EvidenceSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    result: Result
    signal: str
    independence_group: str

    @field_validator("signal", "independence_group")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value


class EvaluationCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    category: str
    phone_number: str
    context: RequestContext
    expected_safe_decision: Decision
    rationale: str
    scenario: dict[Action, EvidenceSpec]

    @field_validator("id", "category", "rationale")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value

    @model_validator(mode="after")
    def complete_scenario(self):
        expected = set(SERVABLE_ACTIONS)
        actual = set(self.scenario)
        if actual != expected:
            missing = sorted(action.value for action in expected - actual)
            extra = sorted(action.value for action in actual - expected)
            raise ValueError(f"scenario action mismatch; missing={missing}, extra={extra}")
        return self

    def provider_scenario(self) -> dict[Action, tuple[Result, str]]:
        return {
            action: (evidence.result, evidence.signal)
            for action, evidence in self.scenario.items()
        }


class Dataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int
    authorship: str
    limitations: str
    cases: tuple[EvaluationCase, ...]

    @field_validator("authorship", "limitations")
    @classmethod
    def disclosure_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value

    @model_validator(mode="after")
    def unique_cases(self):
        ids = [case.id for case in self.cases]
        numbers = [case.phone_number for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("case ids must be unique")
        if len(numbers) != len(set(numbers)):
            raise ValueError("case phone numbers must be unique")
        if not ids:
            raise ValueError("dataset must contain at least one case")
        return self


class BaselineResult(BaseModel):
    decision: Decision
    # Provider OPERATIONS, not evidence links. A swap date is a second billable
    # call that adds no link, so counting links understated what Isnad actually
    # spends and overstated the saving against a full-evidence baseline.
    calls: int
    # How many of `calls` were date enrichments rather than evidence checks, so
    # the two are separable rather than silently merged.
    enrichment_calls: int = 0
    adverse_groups: list[str] = []
    unresolved_signals: list[str] = []
    confidence: float | None = None


def load_dataset(path: Path = FIXTURE_PATH) -> Dataset:
    try:
        raw = json.loads(path.read_text())
        return Dataset.model_validate(raw)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        raise ValueError(f"invalid independent-evaluation fixture {path}: {exc}") from exc


def _unresolved(case: EvaluationCase) -> list[str]:
    return sorted(
        evidence.signal
        for evidence in case.scenario.values()
        if evidence.signal in UNRESOLVED_SIGNALS
    )


def corroboration_aware(case: EvaluationCase) -> BaselineResult:
    """A full-evidence rule that discounts correlated adverse answers.

    A decline requires FLAG results from at least two independence groups. One
    adverse group or any unanswered check produces CHALLENGE. This comparator
    is intentionally stronger than an any-flag rule and makes its independence
    assumption reviewable in the fixture itself.
    """
    groups = sorted(
        {
            evidence.independence_group
            for evidence in case.scenario.values()
            if evidence.result == Result.FLAG
        }
    )
    unresolved = _unresolved(case)
    if len(groups) >= 2:
        decision = Decision.DECLINE
    elif groups or unresolved:
        decision = Decision.CHALLENGE
    else:
        decision = Decision.ALLOW
    return BaselineResult(
        decision=decision,
        calls=len(SERVABLE_ACTIONS),
        adverse_groups=groups,
        unresolved_signals=unresolved,
    )


def full_evidence_same_policy(case: EvaluationCase, engine: PolicyEngine) -> BaselineResult:
    """Apply the shipped prior, deltas, and thresholds after every served check."""
    logodds = engine.prior_logodds(case.context)
    for action in SERVABLE_ACTIONS:
        logodds += engine.signal_delta(case.scenario[action].signal)
    confidence = logodds_to_p(logodds)
    decision = engine.decide(confidence)
    unresolved = _unresolved(case)
    if decision == Decision.ALLOW and unresolved:
        decision = Decision.CHALLENGE
    groups = sorted(
        {
            evidence.independence_group
            for evidence in case.scenario.values()
            if evidence.result == Result.FLAG
        }
    )
    return BaselineResult(
        decision=decision,
        calls=len(SERVABLE_ACTIONS),
        adverse_groups=groups,
        unresolved_signals=unresolved,
        confidence=round(confidence, 3),
    )


async def _run_actual(case: EvaluationCase) -> BaselineResult:
    provider = MockProvider(scenarios={case.phone_number: case.provider_scenario()})
    request = VerificationRequest(phone_number=case.phone_number, context=case.context)
    verdict = await build_investigator(provider).investigate(request, parallel=False)
    # An enrichment that never left the process (`unsupported`, or one the
    # budget could not cover) is not a call and is not counted.
    enrichments = sum(
        1
        for link in verdict.chain
        if link.timing is not None
        and link.timing.availability not in {"unsupported", "not_attempted"}
    )
    return BaselineResult(
        decision=verdict.decision,
        calls=len(verdict.chain) + enrichments,
        enrichment_calls=enrichments,
        unresolved_signals=sorted(
            {link.signal for link in verdict.chain if link.signal in UNRESOLVED_SIGNALS}
        ),
        confidence=verdict.confidence,
    )


def _method_summary(
    name: str,
    cases: tuple[EvaluationCase, ...],
    results: dict[str, BaselineResult],
    errors: list[dict[str, str]],
) -> dict:
    rows = []
    for case in cases:
        result = results.get(case.id)
        if result is None:
            continue
        rows.append(
            {
                "case_id": case.id,
                "category": case.category,
                "expected_safe_decision": case.expected_safe_decision.value,
                "decision": result.decision.value,
                "matches_authored_expectation": result.decision
                == case.expected_safe_decision,
                "calls": result.calls,
                "enrichment_calls": result.enrichment_calls,
                "confidence": result.confidence,
                "adverse_groups": result.adverse_groups,
                "unresolved_signals": result.unresolved_signals,
            }
        )
    challenges = sum(row["decision"] == Decision.CHALLENGE.value for row in rows)
    automatic = len(rows) - challenges
    calls = [row["calls"] for row in rows]
    disagreements = [row["case_id"] for row in rows if not row["matches_authored_expectation"]]
    return {
        "name": name,
        "coverage": {"evaluated": len(rows), "total": len(cases)},
        "challenge_rate": {
            "count": challenges,
            "total": len(rows),
            "percent": round(100 * challenges / len(rows), 1) if rows else None,
        },
        "automatic_decision_rate": {
            "count": automatic,
            "total": len(rows),
            "percent": round(100 * automatic / len(rows), 1) if rows else None,
        },
        "authored_expectation_disagreements": disagreements,
        "execution_errors": errors,
        "calls": {
            "total": sum(calls),
            "mean": round(mean(calls), 2) if calls else None,
            "min": min(calls) if calls else None,
            "max": max(calls) if calls else None,
        },
        "cases": rows,
    }


async def evaluate(dataset: Dataset) -> dict:
    engine = PolicyEngine(Path(os.environ.get("ISNAD_POLICY_PATH", ROOT / "app/policy/policy.yaml")))
    names = (
        "isnad-greedy",
        "corroboration-aware-rules",
        "full-evidence-same-policy",
    )
    results: dict[str, dict[str, BaselineResult]] = {name: {} for name in names}
    errors: dict[str, list[dict[str, str]]] = {name: [] for name in names}

    for case in dataset.cases:
        for name in names:
            try:
                if name == "isnad-greedy":
                    value = await _run_actual(case)
                elif name == "corroboration-aware-rules":
                    value = corroboration_aware(case)
                else:
                    value = full_evidence_same_policy(case, engine)
                results[name][case.id] = value
            except Exception as exc:  # noqa: BLE001 - errors belong in the evaluation report
                errors[name].append(
                    {"case_id": case.id, "type": type(exc).__name__, "message": str(exc)}
                )

    summaries = {
        name: _method_summary(name, dataset.cases, results[name], errors[name]) for name in names
    }
    pairwise = []
    for case in dataset.cases:
        decisions = {
            name: results[name][case.id].decision.value
            for name in names
            if case.id in results[name]
        }
        if len(set(decisions.values())) > 1:
            pairwise.append(
                {
                    "case_id": case.id,
                    "expected_safe_decision": case.expected_safe_decision.value,
                    "decisions": decisions,
                }
            )

    authored_counts = {
        decision.value: sum(case.expected_safe_decision == decision for case in dataset.cases)
        for decision in Decision
    }
    return {
        "scope": {
            "authorship": dataset.authorship,
            "limitations": dataset.limitations,
            "planner": "greedy",
            "provider": "mock",
            "network_access": False,
        },
        "dataset": {
            "cases": len(dataset.cases),
            "categories": sorted({case.category for case in dataset.cases}),
            "authored_expectations": authored_counts,
            "served_actions_per_full_evidence_case": len(SERVABLE_ACTIONS),
        },
        "methods": summaries,
        "pairwise_disagreements": pairwise,
    }


def render_report(report: dict) -> str:
    dataset = report["dataset"]
    lines = [
        "Independent synthetic evaluation (fixed reviewer-authored cases)",
        report["scope"]["limitations"],
        "",
        (
            f"Dataset coverage: {dataset['cases']} cases; "
            f"{len(dataset['categories'])} scenario categories; "
            f"expected outcomes {dataset['authored_expectations']}"
        ),
        "",
        (
            f"{'method':29} {'completed':9} {'automatic':12} {'challenge':12} "
            f"{'expectation gaps':17} {'errors':6} {'calls total/mean':16}"
        ),
        "-" * 112,
    ]
    for method in report["methods"].values():
        coverage = method["coverage"]
        challenge = method["challenge_rate"]
        automatic = method["automatic_decision_rate"]
        calls = method["calls"]
        lines.append(
            f"{method['name']:29} "
            f"{coverage['evaluated']:>2}/{coverage['total']:<6} "
            f"{automatic['count']:>2}/{automatic['total']:<3} "
            f"({automatic['percent']:>5.1f}%) "
            f"{challenge['count']:>2}/{challenge['total']:<3} "
            f"({challenge['percent']:>5.1f}%) "
            f"{len(method['authored_expectation_disagreements']):>8}         "
            f"{len(method['execution_errors']):>3}    "
            f"{calls['total']:>3}/{calls['mean']:<5.2f}"
        )
    lines.extend(["", "Authored-expectation disagreements:"])
    for method in report["methods"].values():
        gaps = method["authored_expectation_disagreements"]
        lines.append(f"  {method['name']}: {', '.join(gaps) if gaps else 'none'}")
    lines.extend(["", "Cases where methods disagree:"])
    if not report["pairwise_disagreements"]:
        lines.append("  none")
    for row in report["pairwise_disagreements"]:
        decisions = ", ".join(f"{name}={value}" for name, value in row["decisions"].items())
        lines.append(f"  {row['case_id']}: expected={row['expected_safe_decision']}; {decisions}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=FIXTURE_PATH,
        help="fixed JSON fixture (default: tests/fixtures/independent_evaluation.json)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the complete machine-readable report instead of the table",
    )
    args = parser.parse_args()

    report = asyncio.run(evaluate(load_dataset(args.fixture)))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 1 if any(method["execution_errors"] for method in report["methods"].values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
