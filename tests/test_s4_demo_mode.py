"""S4 — demo mode must default off, and the session provider must not follow it."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.main import app
from app.session import manager as session_manager

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


def test_demo_mode_defaults_off():
    """On, it opens unauthenticated write endpoints. Off is the safe rest state."""
    assert Settings.model_fields["demo_mode"].default is False


def test_demo_endpoints_are_gone_with_the_flag_off(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)

    assert client.post("/v1/console/run/act1", headers=AUTH).status_code == 404
    assert client.post("/v1/sessions/ses_whatever/simulate-swap", headers=AUTH).status_code == 404


def test_demo_endpoints_require_a_key_with_the_flag_on():
    """Open, a stranger could fire acts into the judges' console mid-demo."""
    assert client.post("/v1/console/run/act1").status_code == 401
    assert client.post("/v1/sessions/ses_whatever/simulate-swap").status_code == 401


def test_a_bad_key_cannot_drive_the_demo_endpoints():
    bad = {"Authorization": "Bearer not-a-real-key"}
    assert client.post("/v1/console/run/act1", headers=bad).status_code == 401


def test_console_acts_still_cannot_reach_a_billable_provider(monkeypatch):
    """Verified-good behaviour the runbook says to keep: acts hard-code the mock."""
    monkeypatch.setattr(settings, "provider", "nac")
    monkeypatch.setattr(settings, "nac_api_key", None)  # any real call would 503

    response = client.post("/v1/console/run/act1", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["decision"] == "ALLOW"


@pytest.mark.asyncio
async def test_sessions_follow_the_configured_provider_not_the_demo_flag(monkeypatch):
    """The separate bug in the same flag.

    routes_session.py forced MockProvider whenever demo_mode was on, even under
    ISNAD_PROVIDER=nac, while /v1/verify honoured the provider. One endpoint was
    live and the other scripted, with nothing visible to tell them apart.
    """
    captured: dict = {}

    class StubNacProvider:
        def __init__(self, *args, **kwargs):
            pass

        async def gather(self, action, request):  # pragma: no cover - never polled
            raise AssertionError("not reached in this test")

    from app import providers

    real_create = session_manager.sessions.create

    async def spy(phone_number, ttl_seconds=None, poll_seconds=None, provider=None):
        captured["provider"] = provider
        return await real_create(
            phone_number, ttl_seconds=ttl_seconds, poll_seconds=poll_seconds, provider=provider
        )

    def fake_get_provider(number_verification_token=None):
        return StubNacProvider() if settings.provider == "nac" else providers.get_provider()

    monkeypatch.setattr(settings, "provider", "nac")
    monkeypatch.setattr(settings, "demo_mode", True)  # on, and it must not matter
    monkeypatch.setattr("app.api.deps.get_provider", fake_get_provider)
    monkeypatch.setattr(session_manager.sessions, "create", spy)

    response = client.post(
        "/v1/sessions", headers=AUTH, json={"phone_number": "+962790000009", "ttl_seconds": 1}
    )
    assert response.status_code == 200
    client.delete(f"/v1/sessions/{response.json()['session_id']}", headers=AUTH)

    assert isinstance(captured["provider"], StubNacProvider), (
        "demo_mode still forces the mock provider onto sessions"
    )
