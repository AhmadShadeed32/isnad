"""A reviewer may lend the demo a Gemini key for one request, and no longer.

The feature exists so a judge can watch the agent choose without editing a
`.env` or being handed ours. Everything worth testing about it is a negative:
the key must not outlive the request, reach storage, reach a receipt, come back
in a response, or work at all on a deployment that can spend money.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import runtime_keys
from app.agent.gemini import GeminiClient
from app.api.request_key import RequestKeyMiddleware
from app.config import settings
from app.main import app

AUTH = {"Authorization": "Bearer demo-merchant-key"}
KEY = "AIzaSyTEST-reviewer-supplied-key-000000001"
HEADER = {"X-Isnad-Gemini-Key": KEY}

BODY = {
    "phone_number": "+99999991006",
    "context": {
        "event": "checkout",
        "payment_method": "cod",
        "account_age_days": 0,
        "amount": {"value": 1500, "currency": "USD"},
    },
}


@pytest.fixture(autouse=True)
def model_calls(monkeypatch):
    """Record keys at the model boundary; no test may contact Gemini."""
    calls = []
    outbound = []

    def generate_json(client, **kwargs):
        calls.append(client._api_key)
        return {"action": "stop", "rationale": "Recorded model response"}

    def generate_text(client, **kwargs):
        calls.append(client._api_key)
        return "Recorded model explanation."

    def reject_network(*args, **kwargs):
        outbound.append(args)
        raise AssertionError("Unexpected outbound model request")

    monkeypatch.setattr(GeminiClient, "generate_json", generate_json)
    monkeypatch.setattr(GeminiClient, "generate_text", generate_text)
    monkeypatch.setattr(httpx, "post", reject_network)
    yield calls
    # Model code may catch exceptions, so assert outside that fallback boundary.
    assert not outbound


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _verify(client, *, idem: str, headers: dict | None = None):
    return client.post(
        "/v1/verify",
        headers={**AUTH, "Idempotency-Key": idem, **(headers or {})},
        json=BODY,
    )


# --- the key reaches the model client, and only from the request -------------


def test_a_supplied_key_is_what_the_model_client_would_use(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "", False)
    token = runtime_keys.set_request_gemini_key(KEY)
    try:
        assert runtime_keys.effective_gemini_key() == KEY
    finally:
        runtime_keys.reset_request_gemini_key(token)


def test_a_supplied_key_outranks_a_configured_one(monkeypatch):
    """A reviewer asked for the run to be theirs; it should not quietly be ours."""
    monkeypatch.setattr(settings, "gemini_api_key", "server-key", False)
    token = runtime_keys.set_request_gemini_key(KEY)
    try:
        assert runtime_keys.effective_gemini_key() == KEY
    finally:
        runtime_keys.reset_request_gemini_key(token)
    assert runtime_keys.effective_gemini_key() == "server-key"


def test_without_a_request_key_the_configured_one_still_answers(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "server-key", False)
    assert runtime_keys.request_gemini_key() is None
    assert runtime_keys.effective_gemini_key() == "server-key"


@pytest.mark.parametrize(
    "junk",
    ["", "   ", "x" * 500, "has\nnewline", "has\x00null"],
)
def test_an_unusable_value_is_dropped_rather_than_forwarded(junk):
    """A stray header must not become a confusing upstream error that quotes it."""
    token = runtime_keys.set_request_gemini_key(junk)
    try:
        assert runtime_keys.request_gemini_key() is None
    finally:
        runtime_keys.reset_request_gemini_key(token)


# --- lifetime is exactly one request ----------------------------------------


def test_the_key_does_not_survive_into_the_next_request(client, monkeypatch, model_calls):
    """Workers are reused. A key left bound would be spent by whoever asked next."""
    monkeypatch.setattr(settings, "gemini_api_key", "", False)

    assert _verify(client, idem="key-leak-1", headers=HEADER).status_code == 200
    assert model_calls and set(model_calls) == {KEY}
    model_calls.clear()
    assert _verify(client, idem="key-leak-2").status_code == 200
    assert model_calls == []


def test_nothing_is_bound_once_the_response_has_been_sent(client, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "", False)
    client.get("/health", headers=HEADER)
    assert runtime_keys.request_gemini_key() is None


# --- the key never lands anywhere it could be read later ---------------------


def test_the_key_is_absent_from_the_response_the_reviewer_gets_back(client, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "", False)
    response = _verify(client, idem="key-echo-1", headers=HEADER)

    assert response.status_code == 200
    assert KEY not in response.text
    assert KEY not in json.dumps(dict(response.headers))


def test_the_key_is_absent_from_the_signed_receipt(client, monkeypatch):
    """The receipt is the durable artefact. A credential inside one is forever."""
    monkeypatch.setattr(settings, "gemini_api_key", "", False)
    chain_id = _verify(client, idem="key-receipt-1", headers=HEADER).json()["chain_id"]

    receipt = client.get(f"/v1/receipts/{chain_id}", headers=AUTH)

    assert receipt.status_code == 200
    assert KEY not in receipt.text


def test_the_key_is_absent_from_every_stored_row(client, monkeypatch):
    """Not the chain, not the operations table, not an event — anywhere."""
    from sqlalchemy import inspect, text

    from app.db.database import SessionLocal, engine

    monkeypatch.setattr(settings, "gemini_api_key", "", False)
    _verify(client, idem="key-storage-1", headers=HEADER)

    offenders: list[str] = []
    with SessionLocal() as session:
        for table in inspect(engine).get_table_names():
            rows = session.execute(text(f"SELECT * FROM {table}")).fetchall()
            for row in rows:
                if any(KEY in str(value) for value in row):
                    offenders.append(table)
                    break
    assert not offenders, f"the supplied key was stored in: {sorted(set(offenders))}"


# --- a deployment that can spend money ignores the header entirely -----------


def test_a_non_demo_deployment_refuses_to_take_a_key_from_a_stranger(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False, False)
    assert runtime_keys.accepts_request_key() is False


def test_a_billable_deployment_refuses_even_in_demo_mode(monkeypatch):
    """demo_mode and the provider are configured separately; take the safer read."""
    monkeypatch.setattr(settings, "demo_mode", True, False)
    monkeypatch.setattr(settings, "provider", "nac", False)
    assert runtime_keys.accepts_request_key() is False


def test_the_offline_demo_does_accept_one(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True, False)
    monkeypatch.setattr(settings, "provider", "mock", False)
    assert runtime_keys.accepts_request_key() is True


def test_the_middleware_binds_nothing_when_the_deployment_refuses(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False, False)
    client.get("/health", headers=HEADER)
    assert runtime_keys.request_gemini_key() is None


# --- lending a key is a request to run the agent -----------------------------


def test_a_supplied_key_selects_the_model_planner_on_a_greedy_deployment(monkeypatch):
    """The offline demo runs greedy so the written guide stays true. Handing it
    a key is precisely the request to stop doing that; without this the panel
    that accepts the key would be decorative."""
    from app.agent.planner import LLMPlanner, effective_planner, get_planner
    from app.policy.engine import get_engine

    monkeypatch.setattr(settings, "planner", "greedy", False)
    monkeypatch.setattr(settings, "gemini_api_key", "", False)
    engine = get_engine(str(settings.policy_path))

    assert effective_planner() == "greedy"

    token = runtime_keys.set_request_gemini_key(KEY)
    try:
        assert isinstance(get_planner(engine), LLMPlanner)
        assert effective_planner() == "llm"
    finally:
        runtime_keys.reset_request_gemini_key(token)

    # And the deployment goes straight back to deterministic for everyone else.
    assert effective_planner() == "greedy"


def test_no_key_anywhere_still_reports_greedy(monkeypatch):
    """A run must never advertise an agent that is not going to choose."""
    from app.agent.planner import effective_planner

    monkeypatch.setattr(settings, "planner", "llm", False)
    monkeypatch.setattr(settings, "gemini_api_key", "", False)
    assert effective_planner() == "greedy"


def _scope(key=None):
    return {
        "type": "http",
        "headers": [(b"x-isnad-gemini-key", key.encode())] if key else [],
    }


async def _unused(*args):
    pass


@pytest.mark.parametrize("fails", [False, True])
async def test_request_cleanup_in_the_same_worker_context(monkeypatch, fails):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    observed = []

    async def endpoint(scope, receive, send):
        observed.append(runtime_keys.request_gemini_key())
        if fails and len(observed) == 1:
            raise RuntimeError("Endpoint failed")

    middleware = RequestKeyMiddleware(endpoint)
    if fails:
        with pytest.raises(RuntimeError, match="Endpoint failed"):
            await middleware(_scope(KEY), _unused, _unused)
    else:
        await middleware(_scope(KEY), _unused, _unused)
    assert runtime_keys.request_gemini_key() is None
    await middleware(_scope(), _unused, _unused)
    assert observed == [KEY, None]


async def test_concurrent_requests_keep_their_own_model_keys(monkeypatch, model_calls):
    from app.agent.planner import LLMPlanner

    monkeypatch.setattr(settings, "gemini_api_key", "")
    all_entered = asyncio.Event()
    entered = 0
    observed = []

    async def endpoint(scope, receive, send):
        nonlocal entered
        before = runtime_keys.request_gemini_key()
        entered += 1
        if entered == 3:
            all_entered.set()
        await asyncio.wait_for(all_entered.wait(), timeout=2)

        def use_model():
            client = LLMPlanner._maybe_client()
            if client:
                client.generate_json(system="", prompt="", max_tokens=10)
            return runtime_keys.request_gemini_key()

        after = await asyncio.to_thread(use_model)
        observed.append((before, after))

    middleware = RequestKeyMiddleware(endpoint)
    second_key = KEY + "-second"
    await asyncio.gather(*(
        middleware(_scope(key), _unused, _unused)
        for key in (KEY, second_key, None)
    ))
    assert set(observed) == {(KEY, KEY), (second_key, second_key), (None, None)}
    assert sorted(model_calls) == sorted([KEY, second_key])


@pytest.mark.parametrize("provider,demo_mode", [("mock", False), ("nac", True)])
async def test_refused_headers_never_reach_the_handler(monkeypatch, provider, demo_mode):
    monkeypatch.setattr(settings, "provider", provider)
    monkeypatch.setattr(settings, "demo_mode", demo_mode)
    observed = []

    async def endpoint(scope, receive, send):
        observed.append(runtime_keys.request_gemini_key())

    await RequestKeyMiddleware(endpoint)(_scope(KEY), _unused, _unused)
    assert observed == [None]


def test_explicit_greedy_does_not_call_model_even_with_keys(client, monkeypatch, model_calls):
    monkeypatch.setattr(settings, 'planner', 'llm')
    monkeypatch.setattr(settings, 'gemini_api_key', 'configured-test-key')
    response = _verify(client, idem='explicit-greedy',
                       headers={**HEADER, 'X-Isnad-Planner': 'greedy'})
    assert response.status_code == 200
    assert response.json()['planner'] == 'greedy'
    assert model_calls == []
    response = _verify(client, idem='explicit-llm',
                       headers={**HEADER, 'X-Isnad-Planner': 'llm'})
    assert response.status_code == 200
    assert model_calls and set(model_calls) == {KEY}


async def test_planner_override_is_reset_after_an_exception(monkeypatch):
    monkeypatch.setattr(settings, 'planner', 'llm')

    async def endpoint(scope, receive, send):
        assert runtime_keys.requested_planner() == 'greedy'
        raise RuntimeError('Endpoint failed')

    scope = _scope()
    scope['headers'].append((b'x-isnad-planner', b'greedy'))
    with pytest.raises(RuntimeError):
        await RequestKeyMiddleware(endpoint)(scope, _unused, _unused)
    assert runtime_keys.requested_planner() == 'llm'
