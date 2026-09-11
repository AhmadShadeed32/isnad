"""Space restarts restore the same identity and never overwrite another key."""

import base64
import importlib.util
import os
import stat
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

spec = importlib.util.spec_from_file_location(
    "hf_start", Path(__file__).resolve().parents[1] / "deploy/huggingface/start.py"
)
startup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(startup)


def encoded_key():
    pem = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return pem, base64.b64encode(pem).decode()


def test_restore_same_signing_identity_after_container_replacement(tmp_path, monkeypatch):
    pem, encoded = encoded_key()
    for container in ("first", "replacement"):
        target = tmp_path / container / "vault.pem"
        monkeypatch.setenv("ISNAD_VAULT_KEY_PATH", str(target))
        monkeypatch.setenv(startup.SECRET_NAME, encoded)
        startup.restore_signer()
        assert target.read_bytes() == pem
        assert stat.S_IMODE(target.stat().st_mode) == 0o600
        assert startup.SECRET_NAME not in os.environ


def test_restore_refuses_a_different_existing_key(tmp_path, monkeypatch):
    target = tmp_path / "vault.pem"
    original, _ = encoded_key()
    target.write_bytes(original)
    _, encoded = encoded_key()
    monkeypatch.setenv("ISNAD_VAULT_KEY_PATH", str(target))
    monkeypatch.setenv(startup.SECRET_NAME, encoded)
    with pytest.raises(RuntimeError, match="differs"):
        startup.restore_signer()
    assert target.read_bytes() == original


def test_invalid_signing_secret_is_not_disclosed(tmp_path, monkeypatch):
    monkeypatch.setenv("ISNAD_VAULT_KEY_PATH", str(tmp_path / "vault.pem"))
    monkeypatch.setenv(startup.SECRET_NAME, "invalid-private-material")
    with pytest.raises(RuntimeError) as error:
        startup.restore_signer()
    assert str(error.value) == "The Space signing-key secret is invalid"
