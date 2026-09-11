"""Exercise the real Gemini adapter at its HTTP boundary, with no network."""

import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from app import model_budget, runtime_keys
from app.agent.gemini import GeminiBudgetExhausted, GeminiClient
from app.agent.planner import LLMPlanner
from app.config import settings
from app.domain.enums import Hypothesis
from app.policy.engine import PolicyEngine


@pytest.fixture(autouse=True)
def budget(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "SERVER-KEY")
    monkeypatch.setattr(settings, "llm_max_calls_per_hour", 1)
    model_budget.reset()
    yield
    model_budget.reset()


@pytest.fixture
def transport(monkeypatch):
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["headers"]["x-goog-api-key"])
        return httpx.Response(200, request=httpx.Request("POST", url), json={
            "candidates": [{"content": {"parts": [{
                "text": '{"action":"number_verify","rationale":"Check ownership"}'
            }]}}]
        })

    monkeypatch.setattr("app.agent.gemini.httpx.post", post)
    return calls


def test_cached_planner_stops_spending_at_limit_and_labels_greedy_fallback(transport):
    planner = LLMPlanner(PolicyEngine(settings.policy_path))
    choices = [planner.choose(Hypothesis.ACCOUNT_TAKEOVER, set(), 8) for _ in range(3)]
    assert [choice.source for choice in choices] == ["llm", "greedy", "greedy"]
    assert all("quota exhausted" in choice.rationale for choice in choices[1:])
    assert transport == ["SERVER-KEY"]
    assert model_budget.calls_in_window() == 1


def test_concurrent_clients_cannot_reserve_the_same_remaining_slots(transport, monkeypatch):
    monkeypatch.setattr(settings, "llm_max_calls_per_hour", 3)
    ready = threading.Barrier(16)

    def invoke(_):
        client = GeminiClient("SERVER-KEY", "test-model", 1)
        ready.wait(timeout=5)
        try:
            client.generate_text("rules", "data", 10)
            return True
        except GeminiBudgetExhausted:
            return False

    with ThreadPoolExecutor(max_workers=16) as pool:
        admitted = list(pool.map(invoke, range(16)))
    assert sum(admitted) == len(transport) == model_budget.calls_in_window() == 3


def test_transport_charges_cached_key_even_when_request_context_changes(transport):
    server = GeminiClient("SERVER-KEY", "test-model", 1)
    own = GeminiClient("OWN-KEY", "test-model", 1)
    token = runtime_keys.set_request_gemini_key("OWN-KEY")
    try:
        server.generate_text("rules", "data", 10)
        with pytest.raises(GeminiBudgetExhausted):
            server.generate_text("rules", "data", 10)
    finally:
        runtime_keys.reset_request_gemini_key(token)
    own.generate_text("rules", "data", 10)
    assert transport == ["SERVER-KEY", "OWN-KEY"]
    assert model_budget.calls_in_window() == 1


def test_copying_server_key_into_request_header_does_not_bypass_limit(transport):
    token = runtime_keys.set_request_gemini_key("SERVER-KEY")
    try:
        planner = LLMPlanner(PolicyEngine(settings.policy_path))
        assert planner.choose(Hypothesis.ACCOUNT_TAKEOVER, set(), 8).source == "llm"
        assert runtime_keys.effective_gemini_key() is None
        assert planner.choose(Hypothesis.ACCOUNT_TAKEOVER, set(), 8).source == "greedy"
    finally:
        runtime_keys.reset_request_gemini_key(token)
    assert transport == ["SERVER-KEY"]


def test_failed_attempt_keeps_slot_until_window_expires(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(model_budget.time, "monotonic", lambda: now[0])
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise httpx.ReadTimeout("No response")

    monkeypatch.setattr("app.agent.gemini.httpx.post", fail)
    client = GeminiClient("SERVER-KEY", "test-model", 1)
    with pytest.raises(httpx.ReadTimeout):
        client.generate_text("rules", "data", 10)
    with pytest.raises(GeminiBudgetExhausted):
        client.generate_text("rules", "data", 10)
    assert len(calls) == model_budget.calls_in_window() == 1
    now[0] += model_budget.WINDOW_SECONDS
    with pytest.raises(httpx.ReadTimeout):
        client.generate_text("rules", "data", 10)
    assert len(calls) == 2
    assert model_budget.calls_in_window() == 1
