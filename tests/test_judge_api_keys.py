"""A judge mints a merchant key behind the access code and calls the API with it.

The questions, in order: can a session without the code get a key (no), does
the key work where a configured merchant key works (yes), is the chain it
creates the judge's own (yes, and no other judge's), does the key outlive the
session that minted it (yes, until its own TTL), and is it ever issued where
the default provider bills (no). Nothing here reaches a network.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.api import demo_token
from app.config import settings
from app.judge.access import API_KEY_PREFIX
from app.judge.access import access as judge_access

ACCESS_CODE = "organizer-code-for-tests"

VERIFY_BODY = {
    "phone_number": "+99999991006",
    "context": {
        "event": "checkout",
        "payment_method": "cod",
        "account_age_days": 0,
        "amount": {"value": 1500, "currency": "USD"},
        "claimed_location": {"lat": 31.9539, "lon": 35.9106, "radius_m": 2000},
    },
}


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    judge_access.clear()
    demo_token.clear()
    from app.api import rate_limit

    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()
    monkeypatch.setattr(settings, "judge_access_codes", ACCESS_CODE)
    monkeypatch.setattr(settings, "provider", "mock")
    monkeypatch.setattr(settings, "planner", "greedy")
    monkeypatch.setattr(settings, "gemini_api_key", None)
    yield
    judge_access.clear()


@pytest.fixture
def client():
    from app.main import create_app

    return TestClient(create_app())


def start(client) -> str:
    return client.post("/v1/judge/session").json()["session"]


def mint(client, token, code=ACCESS_CODE):
    return client.post(
        "/v1/judge/api-keys", headers={"X-Judge-Session": token}, json={"access_code": code}
    )


def bearer(key: str) -> dict:
    return {"Authorization": f"Bearer {key}"}


# --- issuance ----------------------------------------------------------------


def test_a_key_is_only_minted_behind_the_access_code(client):
    token = start(client)

    refused = mint(client, token, code="not-the-code")
    assert refused.status_code == 403
    assert refused.json()["detail"]["code"] == "invalid_access_code"

    issued = mint(client, token)
    assert issued.status_code == 201, issued.text
    body = issued.json()
    assert body["api_key"].startswith(API_KEY_PREFIX)
    assert 0 < body["expires_in_seconds"] <= settings.judge_api_key_ttl_seconds
    assert body["provider"] == "mock"
    # The exchange never grants the Nokia capability as a side effect.
    assert body["capabilities"]["allowance"]["nac_capability"] is False


def test_minting_needs_a_judge_session_not_a_demo_token(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    public = demo_token.mint()

    no_session = client.post("/v1/judge/api-keys", json={"access_code": ACCESS_CODE})
    as_demo = client.post(
        "/v1/judge/api-keys",
        headers={"X-Judge-Session": public},
        json={"access_code": ACCESS_CODE},
    )

    assert no_session.status_code == 401
    assert as_demo.status_code == 401


def test_the_code_never_comes_back_and_the_key_is_shown_once(client):
    token = start(client)
    issued = mint(client, token).json()

    listing = client.get("/v1/judge/api-keys", headers={"X-Judge-Session": token})

    assert ACCESS_CODE not in issued["prefix"]
    assert ACCESS_CODE not in listing.text
    keys = listing.json()["keys"]
    assert len(keys) == 1
    assert keys[0]["api_key"] is None
    assert keys[0]["prefix"] == issued["prefix"]
    assert issued["api_key"] not in listing.text


def test_keys_are_refused_where_the_default_provider_bills(client, monkeypatch):
    monkeypatch.setattr(settings, "provider", "nac")
    token = start(client)

    response = mint(client, token)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "api_keys_disabled"
    capabilities = client.get("/v1/judge/capabilities").json()
    assert capabilities["api_keys"]["available"] is False


def test_the_capabilities_advertise_the_mint(client):
    body = client.get("/v1/judge/capabilities").json()["api_keys"]

    assert body == {
        "available": True,
        "requires_access": True,
        "ttl_seconds": settings.judge_api_key_ttl_seconds,
        "provider": "mock",
        "planner_default": "greedy",
    }


# --- what the key authorizes --------------------------------------------------


def test_the_key_verifies_like_a_merchant_key_and_the_chain_is_the_judges(client):
    token = start(client)
    key = mint(client, token).json()["api_key"]

    verified = client.post("/v1/verify", headers=bearer(key), json=VERIFY_BODY)
    assert verified.status_code == 200, verified.text
    chain_id = verified.json()["chain_id"]
    assert verified.json()["decision"] == "CHALLENGE"

    # Readable with the key, and with the session that minted the key: they are
    # one tenant. The page that minted the key can show the terminal's receipt.
    with_key = client.get(f"/v1/chains/{chain_id}", headers=bearer(key))
    with_session = client.get(f"/v1/chains/{chain_id}", headers={"X-Judge-Session": token})
    signature = client.get(f"/v1/chains/{chain_id}/verification", headers=bearer(key))

    assert with_key.status_code == 200
    assert with_session.status_code == 200
    assert signature.status_code == 200 and signature.json()["valid"] is True


def test_one_judges_key_cannot_read_another_judges_chain(client):
    mine, theirs = start(client), start(client)
    my_key = mint(client, mine).json()["api_key"]
    their_key = mint(client, theirs).json()["api_key"]

    chain_id = client.post("/v1/verify", headers=bearer(my_key), json=VERIFY_BODY).json()["chain_id"]

    assert client.get(f"/v1/chains/{chain_id}", headers=bearer(their_key)).status_code == 404
    assert client.get(f"/v1/chains/{chain_id}", headers={"X-Judge-Session": theirs}).status_code == 404
    listing = client.get("/v1/judge/api-keys", headers={"X-Judge-Session": theirs}).json()["keys"]
    assert [k["prefix"] for k in listing] != [my_key[:10] + "…"]


def test_the_key_outlives_the_session_that_minted_it(client, monkeypatch):
    token = start(client)
    key = mint(client, token).json()["api_key"]
    session_ttl = settings.judge_session_ttl_seconds
    key_ttl = settings.judge_api_key_ttl_seconds
    assert key_ttl > session_ttl

    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + session_ttl + 1)

    assert client.get("/v1/judge/capabilities", headers={"X-Judge-Session": token}).json()["allowance"]["session"] is False
    still = client.post("/v1/verify", headers=bearer(key), json=VERIFY_BODY)
    assert still.status_code == 200

    monkeypatch.setattr(time, "time", lambda: real_time() + key_ttl + 1)
    gone = client.post("/v1/verify", headers=bearer(key), json=VERIFY_BODY)
    assert gone.status_code == 403
    assert gone.json()["detail"]["code"] == "invalid_api_key"


def test_a_key_is_not_a_judge_session(client):
    token = start(client)
    key = mint(client, token).json()["api_key"]

    response = client.post(
        "/v1/judge/run",
        headers={"X-Judge-Session": key},
        json={"evidence_source": "mock_nokia", "scenario": "swapped_subscriber", "planner": "greedy"},
    )

    assert response.status_code == 401


def test_a_generate_loop_is_throttled_then_the_store_is_bounded(client):
    """Two limits, in the order a loop meets them: the per-session rate limit
    refuses the burst first, and the store itself holds a fixed number."""
    from app.judge import access as module

    token = start(client)
    statuses = {mint(client, token).status_code for _ in range(70)}
    assert statuses == {201, 429}

    session = judge_access.require(token)
    for _ in range(module._MAX_LIVE_API_KEYS + 5):
        judge_access.mint_api_key(token, ACCESS_CODE)
    assert len(judge_access.api_keys_for(session)) == module._MAX_LIVE_API_KEYS


def test_the_page_carries_no_credential(client):
    response = client.get("/api-keys")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "__ISNAD_JUDGE_TOKEN__" not in response.text
    assert "demo_" not in response.text
    assert ACCESS_CODE not in response.text
