"""The fixed synthetic evaluation must expose disagreements, not hide them."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.domain.enums import Decision

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "independent_evaluation", ROOT / "scripts" / "independent_evaluation.py"
)
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


def test_fixed_cases_cover_the_risky_shapes_the_report_claims():
    dataset = evaluation.load_dataset()
    cases = dataset.cases

    assert len(cases) == 13
    assert len({case.id for case in cases}) == len(cases)
    assert {case.expected_safe_decision for case in cases} == set(Decision)
    assert {
        "clean",
        "legitimate_change",
        "unavailable_evidence",
        "single_adverse",
        "correlated_adverse",
        "independent_adverse",
    } <= {case.category for case in cases}
    assert all(case.rationale.strip() for case in cases)


def test_module_overrides_live_configuration_before_app_imports():
    env = os.environ.copy()
    env.update(
        {
            "ISNAD_PROVIDER": "nac",
            "ISNAD_PLANNER": "llm",
            "ISNAD_GEMINI_API_KEY": "must-not-be-used",
            "ISNAD_NAC_API_KEY": "must-not-be-used",
            "ISNAD_MERCHANT_API_KEYS": "must-not-be-used",
        }
    )
    code = (
        "import json; import scripts.independent_evaluation; "
        "from app.config import settings; "
        "print(json.dumps({'provider': settings.provider, 'planner': settings.planner, "
        "'gemini': settings.gemini_api_key, 'nac': settings.nac_api_key, "
        "'merchant': settings.merchant_api_keys}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {
        "provider": "mock",
        "planner": "greedy",
        "gemini": "",
        "nac": "",
        "merchant": "",
    }


def test_corroboration_baseline_does_not_double_count_one_change_event():
    cases = {case.id: case for case in evaluation.load_dataset().cases}

    correlated = evaluation.corroboration_aware(cases["correlated_sim_and_device_change"])
    independent = evaluation.corroboration_aware(cases["replacement_plus_location_mismatch"])

    assert correlated.decision == Decision.CHALLENGE
    assert independent.decision == Decision.DECLINE
    assert correlated.calls == independent.calls == len(evaluation.SERVABLE_ACTIONS)


def test_unavailable_evidence_is_a_gap_and_never_an_adverse_vote():
    cases = {case.id: case for case in evaluation.load_dataset().cases}
    result = evaluation.corroboration_aware(cases["multiple_provider_gaps"])

    assert result.decision == Decision.CHALLENGE
    assert result.adverse_groups == []
    assert set(result.unresolved_signals) == {
        "CONSENT_REQUIRED",
        "PROVIDER_UNAVAILABLE",
        "EVIDENCE_UNAVAILABLE",
        "LOCATION_UNKNOWN",
    }


@pytest.mark.asyncio
async def test_report_accounts_for_every_case_call_and_disagreement():
    report = await evaluation.evaluate(evaluation.load_dataset())
    total = report["dataset"]["cases"]

    assert report["dataset"]["authored_expectations"] == {
        "ALLOW": 2,
        "CHALLENGE": 8,
        "DECLINE": 3,
    }
    for method in report["methods"].values():
        assert method["coverage"] == {"evaluated": total, "total": total}
        assert method["execution_errors"] == []
        assert method["calls"]["total"] == sum(row["calls"] for row in method["cases"])

    actual = report["methods"]["isnad-greedy"]
    full = report["methods"]["full-evidence-same-policy"]
    assert actual["calls"]["total"] < full["calls"]["total"]
    assert full["calls"]["total"] == total * len(evaluation.SERVABLE_ACTIONS)

    # A useful comparison contains concrete differences. If this becomes empty,
    # either behaviour changed and expectations need review, or the baselines
    # accidentally collapsed into the implementation under test.
    assert report["pairwise_disagreements"]
    disagreeing = {row["case_id"] for row in report["pairwise_disagreements"]}
    assert "number_and_location_mismatch" in disagreeing

    # `correlated_sim_and_device_change` used to be pinned here and no longer
    # disagrees, which is the ALLOW gate working rather than the comparison
    # collapsing: greedy used to stop early on a check that could not speak to
    # the hypothesis, and now buys one that can. It reaches the same answer as
    # both baselines AND the authored expectation, on fewer calls — which is
    # the claim this whole comparison exists to support, so it is asserted
    # rather than quietly dropped.
    converged = "correlated_sim_and_device_change"
    assert converged not in disagreeing
    rows = {
        name: next(c for c in method["cases"] if c["case_id"] == converged)
        for name, method in report["methods"].items()
    }
    assert len({row["decision"] for row in rows.values()}) == 1
    assert rows["isnad-greedy"]["decision"] == rows["isnad-greedy"]["expected_safe_decision"]
    assert rows["isnad-greedy"]["calls"] < rows["full-evidence-same-policy"]["calls"]


def test_dataset_validation_rejects_an_implicit_safety_label(tmp_path):
    source = evaluation.FIXTURE_PATH.read_text()
    broken = tmp_path / "broken.json"
    broken.write_text(source.replace('"expected_safe_decision": "ALLOW",', '"expected_safe_decision": "",', 1))

    with pytest.raises(ValueError, match="expected_safe_decision"):
        evaluation.load_dataset(broken)
