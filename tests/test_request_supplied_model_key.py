"""A reviewer may lend the demo a Gemini key for one request, and no longer.

The feature exists so a judge can watch the agent choose without editing a
`.env` or being handed ours. Everything worth testing about it is a negative:
the key must not outlive the request, reach storage, reach a receipt, come back
in a response, or work at all on a deployment that can spend money.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import runtime_keys
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


def test_the_key_does_not_survive_into_the_next_request(client, monkeypatch):
    """Workers are reused. A key left bound would be spent by whoever asked next."""
    monkeypatch.setattr(settings, "gemini_api_key", "", False)

    assert _verify(client, idem="key-leak-1", headers=HEADER).status_code == 200
    # A second request that supplies nothing must see nothing.
    assert runtime_keys.request_gemini_key() is None
    assert _verify(client, idem="key-leak-2").status_code == 200
    assert runtime_keys.effective_gemini_key() is None or (
        runtime_keys.effective_gemini_key() != KEY
    )


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
