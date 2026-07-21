"""LLM planner fallback + cache/idempotency."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.agent.planner import GreedyPlanner, LLMPlanner, get_planner
from app.cache import InMemoryCache
from app.config import settings
from app.domain.enums import Action, Hypothesis
from app.main import app
from app.policy.engine import PolicyEngine

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


def _engine() -> PolicyEngine:
    return PolicyEngine(settings.policy_path)


def test_llm_planner_falls_back_to_greedy_without_key():
    """With no API key, the LLM planner must behave exactly like greedy."""
    eng = _engine()
    llm = LLMPlanner(eng)
    greedy = GreedyPlanner(eng)
    assert llm._client is None
    a_llm = llm.next_best(Hypothesis.ACCOUNT_TAKEOVER, set(), 8.0)
    a_greedy = greedy.next_best(Hypothesis.ACCOUNT_TAKEOVER, set(), 8.0)
    assert a_llm == a_greedy == Action.NUMBER_VERIFY


def test_planner_factory_selects_by_config(monkeypatch):
    monkeypatch.setattr(settings, "planner", "llm")
    assert isinstance(get_planner(_engine()), LLMPlanner)
    monkeypatch.setattr(settings, "planner", "greedy")
    assert isinstance(get_planner(_engine()), GreedyPlanner)


def test_in_memory_cache_ttl():
    c = InMemoryCache()
    c.set("k", "v", ttl_seconds=10)
    assert c.get("k") == "v"
    c.set("k2", "v2", ttl_seconds=0)  # 0 -> no expiry in this impl
    assert c.get("k2") == "v2"


def test_idempotency_key_replays_same_verdict():
    body = {"phone_number": "+962790000002",
            "context": {"event": "checkout", "payment_method": "cod",
                        "account_age_days": 0, "amount": {"value": 4200}}}
    h = {**AUTH, "Idempotency-Key": f"order-{time.time()}"}
    r1 = client.post("/v1/verify", headers=h, json=body)
    r2 = client.post("/v1/verify", headers=h, json=body)
    assert r1.status_code == r2.status_code == 200
    # Same key -> same chain (not re-investigated).
    assert r1.json()["chain_id"] == r2.json()["chain_id"]


def test_no_idempotency_key_creates_new_chains():
    body = {"phone_number": "+962790000001",
            "context": {"event": "signup", "account_age_days": 0}}
    r1 = client.post("/v1/verify", headers=AUTH, json=body)
    r2 = client.post("/v1/verify", headers=AUTH, json=body)
    assert r1.json()["chain_id"] != r2.json()["chain_id"]
