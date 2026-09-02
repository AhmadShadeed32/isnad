from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.events import emit, subscribe
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


def test_idempotency_key_rejects_a_different_request_body():
    headers = {**AUTH, "Idempotency-Key": "same-order"}
    first = client.post(
        "/v1/verify",
        headers=headers,
        json={"phone_number": "+962790000001", "context": {"event": "signup"}},
    )
    second = client.post(
        "/v1/verify",
        headers=headers,
        json={"phone_number": "+962790000002", "context": {"event": "signup"}},
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "idempotency_key_reused"


def test_phone_number_validation_rejects_unusable_input():
    response = client.post(
        "/v1/verify",
        headers=AUTH,
        json={"phone_number": "not-a-phone"},
    )

    assert response.status_code == 422


def test_demo_control_is_disabled_outside_demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    response = client.post("/v1/console/run/act1")
    assert response.status_code == 404


def test_missing_nac_credentials_return_provider_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "provider", "nac")
    monkeypatch.setattr(settings, "nac_api_key", None)
    response = client.post(
        "/v1/verify",
        headers=AUTH,
        json={"phone_number": "+99999991001", "context": {"event": "signup"}},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "provider_unavailable"


@pytest.mark.asyncio
async def test_event_bus_masks_phone_numbers():
    async def collect_one() -> dict:
        async for event in subscribe():
            return event
        raise AssertionError("subscriber ended without an event")

    task = asyncio.create_task(collect_one())
    await asyncio.sleep(0)
    await emit({"type": "session", "phone_number": "+962790000001"})
    event = await asyncio.wait_for(task, timeout=1)

    assert event["phone_number"] == "+96…01"
    assert "+962790000001" not in str(event)


def test_suite_never_runs_against_a_billable_provider():
    """A developer's .env must not be able to point the suite at real CAMARA calls.

    `Settings` reads `.env`, so without the pin in conftest a plain `pytest` run
    on a machine set up for live work issues billable network calls. This asserts
    the pin is in force regardless of what the environment said on the way in.
    """
    assert settings.provider == "mock"


def test_suite_never_calls_a_live_model():
    """A developer's .env must not be able to point the suite at a paid model.

    The provider pin above stops billable CAMARA calls; this stops billable LLM
    calls, which arrived the moment ISNAD_PLANNER=llm and a real key were added
    to .env. The symptom was the suite hanging, not failing.
    """
    assert settings.planner == "greedy"
    assert not settings.gemini_api_key
