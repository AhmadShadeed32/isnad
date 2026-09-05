"""Focused contract tests for the offline, judge-reviewable evidence pack."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

SCRIPT = Path("scripts/evidence_pack.py")


@pytest.fixture(scope="module")
def evidence_pack_module():
    # The deliverable is deliberately a directly runnable script, so load that
    # exact entry point rather than duplicating its behavior in a helper module.
    return runpy.run_path(str(SCRIPT))


@pytest.mark.asyncio
async def test_evidence_pack_is_offline_and_verifies_the_stored_chain(
    evidence_pack_module, tmp_path
):
    report = await evidence_pack_module["build_report"](evidence_pack_module["CASES"][:1])

    assert report["scope"] == {
        "provider": "mock",
        "planner": "greedy",
        "network_calls": False,
        "model_provider_calls": False,
        "claim": (
            "This report documents deterministic local fixtures. It is not an "
            "accuracy study, a production-traffic report, or proof of operator availability."
        ),
    }
    scenario = report["scenarios"][0]
    assert scenario["outcome"]["decision"] == "ALLOW"
    assert scenario["orchestration"]["provider_sources"] == ["mock"]
    assert scenario["signed_chain_verification"]["valid"] is True
    assert scenario["signed_chain_verification"]["key_trusted"] is True
    assert scenario["counterfactual"] is not None
    assert scenario["evidence"][0]["scripted_provider_latency_ms"] == 45

    json_path, markdown_path = evidence_pack_module["write_report"](report, tmp_path)
    assert json_path.is_file()
    assert markdown_path.is_file()
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "deterministic local MockProvider" in markdown
    assert "Scripted fixture latency" in markdown
    assert "valid=True" in markdown


def test_evidence_pack_command_works_without_pytest_database_setup(tmp_path):
    import json
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["ISNAD_DATABASE_URL"] = "sqlite://"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-dir", str(tmp_path)],
        capture_output=True, text=True, env=env, check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "evidence-pack.json").read_text())
    assert len(report["scenarios"]) == 5
    assert all(row["signed_chain_verification"]["valid"] for row in report["scenarios"])
