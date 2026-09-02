"""S1 — the merchant API key must not be reachable from the console source."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import demo_token
from app.config import InsecureConfiguration, Settings, check_startup_posture
from app.main import app

client = TestClient(app)


def test_console_source_contains_no_merchant_key():
    """The finding, verbatim: view-source used to yield a working credential."""
    body = client.get("/console").text
    assert "demo-merchant-key" not in body
    assert "__ISNAD_CONSOLE_TOKEN__" not in body  # placeholder was substituted


def test_console_token_authenticates_and_differs_per_render():
    first = _token_from_console()
    second = _token_from_console()
    assert first and second and first != second

    response = client.post(
        "/v1/verify",
        headers={"Authorization": f"Bearer {first}"},
        json={"phone_number": "+99999991001", "context": {"event": "signup"}},
    )
    assert response.status_code == 200


def test_console_token_is_rejected_once_expired(monkeypatch):
    token = _token_from_console()
    monkeypatch.setattr(demo_token, "DEMO_TOKEN_TTL_SECONDS", 0)
    demo_token.clear()
    assert demo_token.is_valid(token) is False


def test_no_token_is_minted_when_demo_mode_is_off(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "demo_mode", False)
    body = client.get("/console").text
    # The placeholder collapses to an empty string, not to a credential.
    assert "CONSOLE_TOKEN = ''" in body
    with pytest.raises(RuntimeError):
        demo_token.mint()


def test_a_console_token_does_not_survive_demo_mode_being_turned_off(monkeypatch):
    token = _token_from_console()
    assert demo_token.is_valid(token) is True

    from app.config import settings

    monkeypatch.setattr(settings, "demo_mode", False)
    assert demo_token.is_valid(token) is False


def test_the_default_configuration_accepts_no_key():
    """An unconfigured instance fails closed rather than shipping a credential.

    Asserted against the field default rather than an instance: the suite exports
    ISNAD_MERCHANT_API_KEYS, and an environment variable outranks `_env_file=None`.
    The default is the thing that used to be a published credential.
    """
    assert Settings.model_fields["merchant_api_keys"].default == ""


def test_startup_refuses_the_published_key_on_the_billable_path():
    with pytest.raises(InsecureConfiguration, match="published demo key"):
        check_startup_posture(
            Settings(
                _env_file=None,
                provider="nac",
                demo_mode=False,
                merchant_api_keys="demo-merchant-key",
            )
        )


def test_startup_refuses_an_empty_key_set_on_the_billable_path():
    with pytest.raises(InsecureConfiguration, match="empty"):
        check_startup_posture(
            Settings(_env_file=None, provider="nac", demo_mode=False, merchant_api_keys="")
        )


def test_startup_refuses_billable_calls_while_demo_mode_is_enabled(tmp_path):
    from app.chain.vault import VaultSigner

    key_path = tmp_path / "vault-key.pem"
    VaultSigner(key_path)
    with pytest.raises(InsecureConfiguration, match="DEMO_MODE=true"):
        check_startup_posture(
            Settings(
                _env_file=None,
                provider="nac",
                demo_mode=True,
                merchant_api_keys="generated-key",
                nac_api_key="test-nac-key",
                subject_pepper="test-pepper",
                vault_key_path=key_path,
                nac_redirect_uri="https://isnad.example/v1/consents/number-verification/callback",
            )
        )


def test_startup_allows_a_real_key_on_the_billable_path(tmp_path):
    # A pepper (S5) and a present vault key (S6) are required alongside it.
    from app.chain.vault import VaultSigner

    key_path = tmp_path / "vault-key.pem"
    VaultSigner(key_path)

    check_startup_posture(
        Settings(
            _env_file=None,
            provider="nac",
            demo_mode=False,
            merchant_api_keys="P7x_generated_key",
            nac_api_key="test-nac-key",
            subject_pepper="a-persisted-pepper",
            vault_key_path=key_path,
            nac_redirect_uri="https://isnad.example/v1/consents/number-verification/callback",
        )
    )


def test_startup_does_not_gate_the_mock_provider():
    """An open mock instance costs nothing and leaks nothing real."""
    check_startup_posture(Settings(_env_file=None, provider="mock", merchant_api_keys=""))


def _token_from_console() -> str:
    body = client.get("/console").text
    marker = "const CONSOLE_TOKEN = '"
    start = body.index(marker) + len(marker)
    return body[start : body.index("'", start)]
