from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.events import emit, subscribe
from app.config import settings
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
