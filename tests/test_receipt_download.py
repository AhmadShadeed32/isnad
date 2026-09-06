"""I7 — portable receipt verification.

The existing GET /v1/receipts/{chain_id} already carries everything an
offline verifier needs (the exact signed bytes, signature, public key,
algorithm) — I7 adds a schema_version so a bundle format can evolve, and an
offline script that verifies it without any request to Isnad.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.chain.models import Verdict
from app.chain.vault import vault
from app.db import store
from app.domain.enums import ChainGrade, Decision
from app.main import app

client = TestClient(app)
REPO_ROOT = Path(__file__).resolve().parents[1]


_counter = iter(range(1_000_000))


@pytest.fixture
def chain_id() -> str:
    verdict = Verdict(
        decision=Decision.ALLOW,
        chain_grade=ChainGrade.ATTESTED_PARTIAL,
        confidence=0.1,
        hypothesis="legit",
        reason="",
        chain_id=f"chn_i7_download_{next(_counter)}",
    )
    store.save(verdict)
    return verdict.chain_id


def test_the_receipt_response_carries_a_schema_version(chain_id):
    data = client.get(f"/v1/receipts/{chain_id}").json()
    assert data["schema_version"] == 1


def _run_verify_script(bundle_path: Path, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "verify_receipt.py"), str(bundle_path), *extra_args],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_the_offline_script_verifies_a_valid_downloaded_bundle(chain_id, tmp_path):
    data = client.get(f"/v1/receipts/{chain_id}").json()
    bundle_path = tmp_path / "receipt.json"
    bundle_path.write_text(json.dumps(data), encoding="utf-8")

    result = _run_verify_script(bundle_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VALID" in result.stdout


def test_the_offline_script_rejects_a_tampered_bundle(chain_id, tmp_path):
    data = client.get(f"/v1/receipts/{chain_id}").json()
    data["signed_payload"] = data["signed_payload"].replace('"ALLOW"', '"DECLINE"')
    bundle_path = tmp_path / "receipt.json"
    bundle_path.write_text(json.dumps(data), encoding="utf-8")

    result = _run_verify_script(bundle_path)
    assert result.returncode != 0
    assert "INVALID" in result.stderr


def test_the_offline_script_rejects_an_untrusted_key(chain_id, tmp_path):
    data = client.get(f"/v1/receipts/{chain_id}").json()
    bundle_path = tmp_path / "receipt.json"
    bundle_path.write_text(json.dumps(data), encoding="utf-8")

    trusted_key_path = tmp_path / "trusted_keys.txt"
    trusted_key_path.write_text("0" * 64 + "\n", encoding="utf-8")  # some other key

    result = _run_verify_script(bundle_path, "--trusted-keys", str(trusted_key_path))
    assert result.returncode != 0
    assert "not in the trusted-key file" in (result.stdout + result.stderr)


def test_the_offline_script_accepts_a_matching_trusted_key(chain_id, tmp_path):
    data = client.get(f"/v1/receipts/{chain_id}").json()
    bundle_path = tmp_path / "receipt.json"
    bundle_path.write_text(json.dumps(data), encoding="utf-8")

    trusted_key_path = tmp_path / "trusted_keys.txt"
    trusted_key_path.write_text(vault.public_key_hex() + "\n", encoding="utf-8")

    result = _run_verify_script(bundle_path, "--trusted-keys", str(trusted_key_path))
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_malformed_bundle_is_rejected_not_crashed(tmp_path):
    bundle_path = tmp_path / "bad.json"
    bundle_path.write_text('{"not": "a receipt"}', encoding="utf-8")
    result = _run_verify_script(bundle_path)
    assert result.returncode != 0
