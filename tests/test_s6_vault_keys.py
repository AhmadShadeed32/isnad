"""S6 — verification must use the key that signed, and survive a restart."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.chain.vault import MissingVaultKey, VaultSigner, resolve_key_path
from app.config import InsecureConfiguration, Settings, check_startup_posture

PAYLOAD = b'{"chain_id":"chn_test","decision":"ALLOW"}'


def test_a_relative_key_path_does_not_depend_on_the_working_directory():
    """The finding, verbatim: config.py made vault_key_path CWD-relative.

    A process started from the wrong directory came up healthy, wrote a second
    key, and then reported every previously signed chain as invalid.
    """
    resolved = resolve_key_path(Path(".isnad/vault-key.pem"))

    assert resolved is not None and resolved.is_absolute()
    assert resolve_key_path(Path(".isnad/vault-key.pem")) == resolved


def test_an_absolute_key_path_is_left_alone(tmp_path):
    target = tmp_path / "vault-key.pem"
    assert resolve_key_path(target) == target


def test_a_chain_signed_before_a_restart_still_verifies(tmp_path):
    """The acceptance criterion: issue, restart, verify."""
    key_path = tmp_path / ".isnad" / "vault-key.pem"

    before = VaultSigner(key_path)
    signature = before.sign(PAYLOAD)
    public_key = before.public_key_hex()

    after = VaultSigner(key_path)  # a fresh process, same volume
    assert after.public_key_hex() == public_key
    assert after.verify_with(public_key, PAYLOAD, signature) is True


def test_verification_uses_the_recorded_key_not_the_live_one(tmp_path):
    """The route returned rec.public_key while verifying with its own."""
    signer = VaultSigner(tmp_path / "a.pem")
    signature = signer.sign(PAYLOAD)
    recorded_key = signer.public_key_hex()

    rotated = VaultSigner(tmp_path / "b.pem")
    assert rotated.public_key_hex() != recorded_key
    # Live key: wrong answer. Recorded key: correct, once it is trusted.
    assert rotated.verify(PAYLOAD, signature) is False
    assert rotated.verify_with(recorded_key, PAYLOAD, signature) is False  # untrusted

    monkeyed = VaultSigner(tmp_path / "b.pem")
    from app.config import settings

    original = settings.vault_trusted_public_keys
    settings.vault_trusted_public_keys = recorded_key
    try:
        assert monkeyed.verify_with(recorded_key, PAYLOAD, signature) is True
    finally:
        settings.vault_trusted_public_keys = original


def test_a_forged_record_cannot_bring_its_own_key(tmp_path):
    """Otherwise a row with a self-consistent key and signature verifies."""
    attacker = VaultSigner(tmp_path / "attacker.pem")
    forged_payload = b'{"chain_id":"chn_test","decision":"ALLOW","forged":true}'
    forged_signature = attacker.sign(forged_payload)

    server = VaultSigner(tmp_path / "server.pem")
    assert server.verify_with(attacker.public_key_hex(), forged_payload, forged_signature) is False
    assert server.trusts(attacker.public_key_hex()) is False


def test_a_malformed_public_key_is_rejected_rather_than_raising(tmp_path):
    signer = VaultSigner(tmp_path / "k.pem")
    signature = signer.sign(PAYLOAD)

    assert signer.verify_with("not-hex", PAYLOAD, signature) is False
    assert signer.verify_with("aabb", PAYLOAD, signature) is False


def test_refusing_to_create_a_key_when_one_was_expected(tmp_path):
    """Silently generating is what turns a missing volume into a stage failure."""
    with pytest.raises(MissingVaultKey):
        VaultSigner(tmp_path / "absent.pem", allow_create=False)


def test_startup_refuses_a_missing_key_on_the_billable_path(tmp_path):
    with pytest.raises(InsecureConfiguration, match="vault signing key"):
        check_startup_posture(
            Settings(
                _env_file=None,
                provider="nac",
                demo_mode=False,
                merchant_api_keys="a-real-key",
                nac_api_key="test-nac-key",
                subject_pepper="a-pepper",
                vault_key_path=tmp_path / "does-not-exist.pem",
            )
        )


def test_startup_accepts_a_key_that_is_actually_there(tmp_path):
    key_path = tmp_path / "vault-key.pem"
    VaultSigner(key_path)  # create it

    check_startup_posture(
        Settings(
            _env_file=None,
            provider="nac",
            demo_mode=False,
            merchant_api_keys="a-real-key",
            nac_api_key="test-nac-key",
            subject_pepper="a-pepper",
            vault_key_path=key_path,
            nac_redirect_uri="https://isnad.example/v1/consents/number-verification/callback",
        )
    )
