"""P4a — demo/merchant_pilot, the single-merchant reference harness.

The harness never receives ISNAD_MERCHANT_API_KEY from the browser, requires
an authenticated operator session with CSRF protection for mutations, and
only accepts loopback/private connections by default. Isnad itself is never
started here — every call it would make is mocked with httpx.MockTransport.
"""

from __future__ import annotations

import os

os.environ.setdefault("ISNAD_MERCHANT_API_KEY", "test-merchant-key")
os.environ.setdefault("PILOT_OPERATOR_USERNAME", "operator")
os.environ.setdefault("PILOT_OPERATOR_PASSWORD", "correct-horse-battery-staple")

import httpx
import pytest
from starlette.testclient import TestClient

import demo.merchant_pilot.app as pilot_module
from demo.merchant_pilot.app import app

LOCAL_CLIENT = ("127.0.0.1", 51000)
PUBLIC_CLIENT = ("8.8.8.8", 51000)


@pytest.fixture(autouse=True)
def _reset_login_throttle():
    pilot_module.login_throttle._failures.clear()
    yield
    pilot_module.login_throttle._failures.clear()


def _client(**kwargs) -> TestClient:
    return TestClient(app, client=LOCAL_CLIENT, **kwargs)


def _patch_isnad(monkeypatch, handler) -> None:
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("base_url", None)
        kwargs.pop("timeout", None)
        return real_client(transport=httpx.MockTransport(handler), base_url=pilot_module.ISNAD_BASE_URL)

    monkeypatch.setattr(pilot_module.httpx, "AsyncClient", factory)


def _login(client: TestClient) -> str:
    response = client.post(
        "/login",
        data={"username": "operator", "password": "correct-horse-battery-staple"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    session_id = client.cookies.get(pilot_module.SESSION_COOKIE)
    assert session_id
    session = pilot_module.sessions.get(session_id)
    assert session is not None
    return session.csrf_token


def test_a_public_client_is_rejected_before_any_route_runs():
    client = TestClient(app, client=PUBLIC_CLIENT)

    response = client.get("/login")

    assert response.status_code == 403


def test_wrong_credentials_are_rejected_and_throttled():
    client = _client()

    for _ in range(pilot_module.login_throttle.max_attempts):
        response = client.post("/login", data={"username": "operator", "password": "wrong"})
        assert response.status_code == 401

    locked_out = client.post("/login", data={"username": "operator", "password": "wrong"})
    assert locked_out.status_code == 429


def test_correct_credentials_start_a_session():
    client = _client()
    csrf = _login(client)

    assert csrf

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert csrf in dashboard.text
    assert pilot_module.ISNAD_MERCHANT_API_KEY not in dashboard.text


def test_the_dashboard_redirects_an_unauthenticated_visitor_to_login():
    client = _client()

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_creating_a_flow_requires_a_session():
    client = _client()

    response = client.post("/api/flows", json={"phone_number": "+15551234567"})

    assert response.status_code == 401


def test_creating_a_flow_requires_a_matching_csrf_token():
    client = _client()
    _login(client)

    no_token = client.post("/api/flows", json={"phone_number": "+15551234567"})
    assert no_token.status_code == 403

    wrong_token = client.post(
        "/api/flows",
        json={"phone_number": "+15551234567"},
        headers={"X-CSRF-Token": "not-the-real-token"},
    )
    assert wrong_token.status_code == 403


def test_a_full_flow_creation_and_completion(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("authorization")
        assert auth == f"Bearer {pilot_module.ISNAD_MERCHANT_API_KEY}"
        if request.url.path == "/v1/consents/number-verification":
            return httpx.Response(
                202,
                json={
                    "consent_id": "cns_test",
                    "status": "PENDING",
                    "authorization_url": "https://consent.test/authorize?state=s",
                    "expires_at": "2026-01-01T00:05:00+00:00",
                    "chain_id": None,
                    "reason": None,
                },
            )
        if request.url.path == "/v1/consents/cns_test":
            return httpx.Response(
                200,
                json={
                    "consent_id": "cns_test",
                    "status": "AUTHORIZED",
                    "authorization_url": "https://consent.test/authorize?state=s",
                    "expires_at": "2026-01-01T00:05:00+00:00",
                    "chain_id": None,
                    "reason": None,
                },
            )
        if request.url.path == "/v1/consents/cns_test/verify":
            return httpx.Response(
                200,
                json={
                    "decision": "ALLOW",
                    "planner": "greedy",
                    "chain_grade": None,
                    "confidence": 0.1,
                    "hypothesis": "h",
                    "reason": "r",
                    "chain_id": "chn_test",
                    "evidence_cost": 0.0,
                    "latency_ms": 1,
                    "evidence_steps": 1,
                    "provider_sources": ["test"],
                },
            )
        raise AssertionError(f"unexpected call to {request.url.path}")

    _patch_isnad(monkeypatch, handler)
    client = _client()
    csrf = _login(client)

    created = client.post(
        "/api/flows",
        json={"phone_number": "+15551234567", "event": "checkout"},
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["flow_id"].startswith("flw_")
    assert "<svg" in body["qr_svg"]
    assert pilot_module.ISNAD_MERCHANT_API_KEY not in created.text

    polled = client.get(f"/api/flows/{body['flow_id']}")
    assert polled.status_code == 200
    polled_body = polled.json()
    assert polled_body["status"] == "COMPLETED"
    assert polled_body["result"]["chain_id"] == "chn_test"
    assert pilot_module.ISNAD_MERCHANT_API_KEY not in polled.text


def test_an_invalid_phone_number_is_rejected(monkeypatch):
    client = _client()
    csrf = _login(client)

    response = client.post(
        "/api/flows",
        json={"phone_number": "not-a-phone-number"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422


def test_logout_clears_the_session():
    client = _client()
    _login(client)

    client.post("/logout", follow_redirects=False)

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
