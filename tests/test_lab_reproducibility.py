"""A published Greedy benchmark must match its standalone reproducible run."""

import asyncio
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import settings
from app.providers import mock
from scripts import build_lab_artifacts, independent_evaluation

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_bundle_ignores_preloaded_host_planner_and_policy(monkeypatch, tmp_path):
    standalone = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, str(ROOT / "scripts/independent_evaluation.py"), "--json"],
        cwd=ROOT,
        env={**os.environ, "ISNAD_PROVIDER": "mock", "ISNAD_GEMINI_API_KEY": ""},
        check=True, capture_output=True, text=True,
    )
    expected = json.loads(standalone.stdout)
    scenarios_before = copy.deepcopy(mock.SCENARIOS)
    # App config is already imported, exactly as it is when building the Lab.
    monkeypatch.setattr(settings, "planner", "llm")
    monkeypatch.setattr(settings, "gemini_api_key", "must-never-be-used")
    monkeypatch.setattr(settings, "policy_path", tmp_path / "not-the-benchmark-policy.yaml")

    def forbidden(*args, **kwargs):
        raise AssertionError("offline recordings selected a deployment planner or called a model")

    monkeypatch.setattr("app.agent.investigator.get_planner", forbidden)
    monkeypatch.setattr("app.agent.gemini.GeminiClient._generate", forbidden)
    bundle = await build_lab_artifacts.build_bundle()
    actual = bundle["evidence_report"]["independent_evaluation"]
    assert actual["methods"] == expected["methods"]
    assert actual["pairwise_disagreements"] == expected["pairwise_disagreements"]
    assert all(not method["execution_errors"] for method in actual["methods"].values())
    assert all(case["run"]["planner_source"] == "greedy" for case in bundle["cases"])
    assert mock.SCENARIOS == scenarios_before


@pytest.mark.asyncio
async def test_committed_lab_evaluation_matches_fresh_greedy_result():
    recorded = json.loads((ROOT / "demo/lab/artifacts/bundle.json").read_text())
    fresh = await independent_evaluation.evaluate(independent_evaluation.load_dataset())
    assert recorded["evidence_report"]["independent_evaluation"]["methods"] == fresh["methods"]
