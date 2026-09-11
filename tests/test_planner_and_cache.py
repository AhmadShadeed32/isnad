"""LLM planner fallback + cache/idempotency."""

from __future__ import annotations

import asyncio
import time
import uuid

import httpx
import pytest
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
    body = {
        "phone_number": "+962790000002",
        "context": {
            "event": "checkout",
            "payment_method": "cod",
            "account_age_days": 0,
            "amount": {"value": 4200},
        },
    }
    h = {**AUTH, "Idempotency-Key": f"order-{time.time()}"}
    r1 = client.post("/v1/verify", headers=h, json=body)
    r2 = client.post("/v1/verify", headers=h, json=body)
    assert r1.status_code == r2.status_code == 200
    # Same key -> same chain (not re-investigated).
    assert r1.json()["chain_id"] == r2.json()["chain_id"]


@pytest.mark.asyncio
async def test_concurrent_idempotent_retries_reserve_one_investigation(monkeypatch):
    """A retry that arrives during paid work must not duplicate that work.

    The second request gets an explicit retryable conflict while the first owns
    the cache reservation; once it completes, the same key replays its result.
    """
    from app.api import routes_verify

    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0
    original_builder = routes_verify.build_investigator

    class SlowInvestigator:
        async def investigate(self, *args, **kwargs):
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return await original_builder(routes_verify.get_live_provider()).investigate(
                *args, **kwargs
            )

    monkeypatch.setattr(routes_verify, "build_investigator", lambda _provider: SlowInvestigator())
    headers = {**AUTH, "Idempotency-Key": f"concurrent-{uuid.uuid4().hex}"}
    body = {"phone_number": "+962790000002", "context": {"event": "checkout"}}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = asyncio.create_task(client.post("/v1/verify", headers=headers, json=body))
        await asyncio.wait_for(started.wait(), timeout=1)
        pending = await client.post("/v1/verify", headers=headers, json=body)
        assert pending.status_code == 409
        assert pending.json()["detail"]["code"] == "idempotency_request_in_progress"
        release.set()
        completed = await first
        replay = await client.post("/v1/verify", headers=headers, json=body)

    assert completed.status_code == replay.status_code == 200
    assert completed.json()["chain_id"] == replay.json()["chain_id"]
    assert calls == 1


def test_no_idempotency_key_creates_new_chains():
    body = {"phone_number": "+962790000001", "context": {"event": "signup", "account_age_days": 0}}
    r1 = client.post("/v1/verify", headers=AUTH, json=body)
    r2 = client.post("/v1/verify", headers=AUTH, json=body)
    assert r1.json()["chain_id"] != r2.json()["chain_id"]


# ---- the CHALLENGE step-up never reaches for an OTP ----

_LOW_FRICTION = {Action.LOCATION_VERIFY, Action.NUMBER_VERIFY, Action.REACHABILITY}


def test_the_step_up_picks_the_cheapest_low_friction_check():
    assert GreedyPlanner(_engine()).cheapest_stepup(set(), 12.0) == Action.NUMBER_VERIFY


def test_the_step_up_never_falls_back_to_an_otp():
    """It used to, and `STEP_UP_OTP` is not a provider call — see
    IMPLEMENTATION_STATUS, "not a network provider call by design". The
    investigator handed it to the provider anyway; no scenario defines it, so
    the catch-all answered `LOCATION_UNKNOWN`, delta 0.0, for a cost of 6. The
    signed chain then carried a link reading like a location check that found
    nothing, and the agent had spent half a high-value budget to learn it.

    CHALLENGE already IS "step this customer up". The merchant sends the OTP,
    in a channel this service does not own; the agent does not claim to have
    watched it happen.
    """
    greedy = GreedyPlanner(_engine())
    # Everything low-friction is spent, and there is budget left over — the
    # exact state the OTP fallback used to fire in.
    assert greedy.engine.action_cost(Action.STEP_UP_OTP) <= 6.0
    assert greedy.cheapest_stepup(set(_LOW_FRICTION), 6.0) is None
    assert greedy.cheapest_stepup(set(Action), 12.0) is None


def test_the_llm_planner_inherits_the_step_up_choreography():
    """The step-up is choreography, not a question for a model. Same trap as
    C1: an invariant asked of a planner holds under greedy and vanishes under
    llm."""
    llm = LLMPlanner(_engine())
    assert llm.cheapest_stepup(set(_LOW_FRICTION), 6.0) is None
    assert llm.cheapest_stepup(set(), 12.0) == Action.NUMBER_VERIFY
