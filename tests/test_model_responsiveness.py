"""A slow model must not block other requests or mix their credentials."""

import asyncio
import threading

import httpx
import pytest

from app.agent.gemini import GeminiClient
from app.config import settings
from app.main import app
from app.runtime_keys import request_gemini_key


@pytest.mark.asyncio
async def test_slow_lab_models_leave_health_responsive_and_preserve_request_keys(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    entered = {key: threading.Event() for key in ("reviewer-one", "reviewer-two")}
    release = threading.Event()
    timeouts = []
    contexts = []

    def blocked_model(client, **kwargs):
        key = client._api_key
        contexts.append((key, request_gemini_key()))
        entered[key].set()
        # A deadline makes a regression fail instead of hanging the test suite.
        if not release.wait(timeout=4):
            timeouts.append(key)
        return {"action": "STOP", "rationale": "Enough evidence for this model test"}

    monkeypatch.setattr(GeminiClient, "generate_json", blocked_model)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        requests = [
            asyncio.create_task(client.post(
                "/v1/lab/run/clean_checkout",
                headers={
                    "Authorization": "Bearer demo-merchant-key",
                    "X-Isnad-Planner": "llm",
                    "X-Isnad-Gemini-Key": key,
                },
            ))
            for key in entered
        ]
        try:
            for event in entered.values():
                assert await asyncio.to_thread(event.wait, 2), "model never started"
            assert not timeouts, "model selection blocked the server event loop"
            assert all(not task.done() for task in requests)
            response = await asyncio.wait_for(client.get("/health"), timeout=1)
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        finally:
            release.set()
            responses = await asyncio.gather(*requests)

    assert all(response.status_code == 200 for response in responses)
    assert set(contexts) == {(key, key) for key in entered}
    assert request_gemini_key() is None
    assert not timeouts
