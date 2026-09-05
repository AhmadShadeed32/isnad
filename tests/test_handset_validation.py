from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "handset_validation.py"


def test_offline_consent_contract_smoke(tmp_path):
    output = tmp_path / "contract.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "contract", "--output", str(output)],
        cwd=SCRIPT.parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["scope"] == {
        "mode": "mock_contract",
        "network_calls": False,
        "physical_handset_reported": False,
        "operator_reported_connection": "none",
        "claim": "Deterministic local route-contract proof; no operator or handset was used.",
    }
    assert report["lifecycle"] == {
        "initiation_status": "PENDING",
        "authorization_status": "AUTHORIZED",
        "completion_status": "COMPLETED",
    }
    assert report["verification"]["number_verification"] == {
        "present_once": True,
        "signal": "NUMBER_MATCH",
        "source": "contract",
        "consent_basis": "NaC authorization / end-user consent",
    }
    assert report["checks"]["oauth_state_single_use"] is True
    assert report["checks"]["callback_replay_http_status"] in {404, 409}
    assert report["checks"]["completion_idempotent"] is True
    assert report["checks"]["receipt_signature_valid"] is True
    artifact = output.read_text(encoding="utf-8")
    assert "+99999991000" not in artifact
    assert "99999991000" not in artifact
    assert "single-use-contract-code" not in artifact
    assert "contract-access-token" not in artifact
    assert output.stat().st_mode & 0o777 == 0o600


def test_live_handset_mode_refuses_to_run_without_explicit_arming(tmp_path):
    env = os.environ.copy()
    env.pop("ISNAD_HANDSET_ARM", None)
    env["ISNAD_HANDSET_API_KEY"] = "must-not-be-printed"
    env["ISNAD_HANDSET_PHONE"] = "+962790000001"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "live",
            "--base-url",
            "https://isnad.invalid",
            "--output",
            str(tmp_path / "must-not-exist.json"),
        ],
        cwd=SCRIPT.parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "refusing live run" in result.stderr
    assert "must-not-be-printed" not in result.stderr
    assert not (tmp_path / "must-not-exist.json").exists()
