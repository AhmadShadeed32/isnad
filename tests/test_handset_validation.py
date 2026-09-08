from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from scripts import handset_validation

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


def _deployment_stub(monkeypatch, *, provider="nac", demo=False, ready=True):
    requests = []
    client_class = httpx.Client

    def respond(request):
        requests.append(request)
        assert request.method == "GET", "preflight must not start OAuth or buy evidence"
        if request.url.path == "/readyz":
            return httpx.Response(200 if ready else 503, json={
                "status": "ready" if ready else "not_ready"
            })
        assert request.url.path == "/v1/console/mode"
        if request.headers.get("Authorization") != "Bearer preflight-private-test":
            return httpx.Response(401, json={"detail": "Authentication required"})
        return httpx.Response(200, json={"provider": provider, "demo_mode": demo})

    monkeypatch.setattr(handset_validation.httpx, "Client", lambda **kwargs: client_class(
        transport=httpx.MockTransport(respond), **kwargs
    ))
    monkeypatch.setenv("ISNAD_HANDSET_API_KEY", "preflight-private-test")
    return requests


def test_preflight_only_checks_http_and_redacts_credential(monkeypatch, tmp_path):
    requests = _deployment_stub(monkeypatch)
    output = tmp_path / "preflight.json"
    args = handset_validation.parse_args([
        "preflight", "--base-url", "https://isnad.invalid", "--output", str(output)
    ])
    report = handset_validation.run_preflight(args)
    assert report["http_checks_passed"] is True
    assert report["manual_checks_remaining"]
    assert report["scope"]["physical_handset_reported"] is False
    assert report["scope"]["oauth_initiated"] is False
    assert report["scope"]["operator_calls"] is False
    assert len(requests) == 3
    assert "preflight-private-test" not in output.read_text()
    assert output.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("provider,demo,ready,blocker", [
    ("mock", True, True, "nac_provider_selected"),
    ("nac", True, True, "demo_disabled"),
    ("nac", False, False, "database_ready"),
])
def test_live_flow_stops_before_oauth_when_preflight_fails(
    monkeypatch, tmp_path, provider, demo, ready, blocker
):
    requests = _deployment_stub(monkeypatch, provider=provider, demo=demo, ready=ready)
    monkeypatch.setenv("ISNAD_HANDSET_ARM", handset_validation.ARM_VALUE)
    monkeypatch.setenv("ISNAD_HANDSET_PHONE", "+99999991000")
    output = tmp_path / "live.json"
    args = handset_validation.parse_args([
        "live", "--base-url", "https://isnad.invalid", "--connection", "mobile-data",
        "--output", str(output),
    ])
    with pytest.raises(handset_validation.ValidationFailure, match=blocker):
        handset_validation.run_live(args)
    assert len(requests) == 3
    assert all("99999991000" not in str(request.url) for request in requests)
    assert not output.exists()


@pytest.mark.parametrize("origin", [
    "http://isnad.invalid", "https://user:secret@isnad.invalid", "https://isnad.invalid/path",
    "https://isnad.invalid?secret=value", "https://isnad.invalid#fragment",
])
def test_preflight_rejects_ambiguous_or_credential_bearing_origin(origin):
    with pytest.raises(handset_validation.ValidationFailure):
        handset_validation._deployment_origin(origin)
