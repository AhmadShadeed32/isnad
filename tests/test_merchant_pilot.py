"""P4a — demo/merchant_pilot, the single-merchant reference harness.

The harness never receives ISNAD_MERCHANT_API_KEY from the browser, requires
an authenticated operator session with CSRF protection for mutations, and
only accepts loopback/private connections by default. Isnad itself is never
started here — every call it would make is mocked with httpx.MockTransport.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

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


def test_an_unsupported_currency_is_rejected_before_calling_isnad(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Isnad must never be called for an unsupported currency")

    _patch_isnad(monkeypatch, handler)
    client = _client()
    csrf = _login(client)
    resp = client.post(
        "/api/flows",
        json={"phone_number": "+15551234567", "amount": {"value": 100, "currency": "JOD"}},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 422


def test_a_claimed_location_is_forwarded_to_isnad(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/consents/number-verification":
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                202,
                json={
                    "consent_id": "cns_loc",
                    "status": "PENDING",
                    "authorization_url": "https://consent.test/authorize?state=s",
                    "expires_at": "2026-01-01T00:05:00+00:00",
                    "chain_id": None,
                    "reason": None,
                },
            )
        raise AssertionError(f"unexpected call to {request.url.path}")

    _patch_isnad(monkeypatch, handler)
    client = _client()
    csrf = _login(client)
    resp = client.post(
        "/api/flows",
        json={
            "phone_number": "+15551234567",
            "claimed_location": {"lat": 31.95, "lon": 35.91, "radius_m": 2000},
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert captured["body"]["context"]["claimed_location"]["lat"] == 31.95


def test_an_invalid_phone_number_is_rejected(monkeypatch):
    client = _client()
    csrf = _login(client)

    response = client.post(
        "/api/flows",
        json={"phone_number": "not-a-phone-number"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422


def test_a_poll_survives_isnad_being_briefly_unreachable(monkeypatch):
    """Found during P4a's browser verification: restarting the Isnad server
    mid-poll produced an unhandled httpx.ConnectError, a 500 to the operator's
    browser, and left `verifying` stuck True so the flow could never complete
    even after Isnad came back."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/consents/number-verification":
            return httpx.Response(
                202,
                json={
                    "consent_id": "cns_flaky",
                    "status": "PENDING",
                    "authorization_url": "https://consent.test/authorize?state=s",
                    "expires_at": "2026-01-01T00:05:00+00:00",
                    "chain_id": None,
                    "reason": None,
                },
            )
        raise httpx.ConnectError("connection refused", request=request)

    _patch_isnad(monkeypatch, handler)
    client = _client()
    csrf = _login(client)
    created = client.post(
        "/api/flows",
        json={"phone_number": "+15551234567"},
        headers={"X-CSRF-Token": csrf},
    )
    flow_id = created.json()["flow_id"]

    polled = client.get(f"/api/flows/{flow_id}")

    assert polled.status_code == 200
    assert polled.json()["status"] == "PENDING"
    flow = pilot_module.flows.get(flow_id)
    assert flow.verifying is False


def _challenge_handler(request: httpx.Request) -> httpx.Response:
    auth = request.headers.get("authorization")
    assert auth == f"Bearer {pilot_module.ISNAD_MERCHANT_API_KEY}"
    if request.url.path == "/v1/consents/number-verification":
        return httpx.Response(
            202,
            json={
                "consent_id": "cns_challenge",
                "status": "PENDING",
                "authorization_url": "https://consent.test/authorize?state=s",
                "expires_at": "2026-01-01T00:05:00+00:00",
                "chain_id": None,
                "reason": None,
            },
        )
    if request.url.path == "/v1/consents/cns_challenge":
        return httpx.Response(
            200,
            json={
                "consent_id": "cns_challenge",
                "status": "AUTHORIZED",
                "authorization_url": "https://consent.test/authorize?state=s",
                "expires_at": "2026-01-01T00:05:00+00:00",
                "chain_id": None,
                "reason": None,
            },
        )
    if request.url.path == "/v1/consents/cns_challenge/verify":
        return httpx.Response(
            200,
            json={
                "decision": "CHALLENGE",
                "planner": "greedy",
                "chain_grade": "DEGRADED",
                "confidence": 0.4,
                "hypothesis": "account_takeover",
                "reason": "r",
                "chain_id": "chn_challenge",
                "evidence_cost": 0.0,
                "latency_ms": 1,
                "evidence_steps": 1,
                "provider_sources": ["test"],
            },
        )
    if request.url.path == "/v1/chains/chn_challenge/challenges":
        assert request.headers.get("idempotency-key") == "pilot-challenge-create-" + _challenge_handler.flow_id
        return httpx.Response(
            201,
            json={
                "attempt_id": "chgat_test",
                "chain_id": "chn_challenge",
                "method": "manual_review",
                "status": "PENDING",
                "created_at": "2026-01-01T00:00:00+00:00",
                "expires_at": "2026-01-01T00:15:00+00:00",
            },
        )
    if request.url.path == "/v1/chains/chn_challenge/challenges/chgat_test/events":
        result = json.loads(request.content)["result"]
        return httpx.Response(
            200,
            json={"attempt_id": "chgat_test", "status": result, "result": result, "reported_at": "2026-01-01T00:01:00+00:00"},
        )
    if request.url.path == "/v1/chains/chn_challenge/outcomes":
        body = json.loads(request.content)
        return httpx.Response(
            201,
            json={
                "event_id": "mout_" + body["dimension"] + "_" + body["value"],
                "chain_id": "chn_challenge",
                "dimension": body["dimension"],
                "value": body["value"],
                "basis": body.get("basis"),
                "occurred_at": body["occurred_at"],
                "reported_at": "2026-01-01T00:02:00+00:00",
                "late_report": False,
                "supersedes_event_id": body.get("supersedes_event_id"),
            },
        )
    raise AssertionError(f"unexpected call to {request.url.path}")


def _make_challenged_flow(monkeypatch, client: TestClient, csrf: str) -> str:
    _patch_isnad(monkeypatch, _challenge_handler)
    created = client.post(
        "/api/flows",
        json={"phone_number": "+15551234567"},
        headers={"X-CSRF-Token": csrf},
    )
    flow_id = created.json()["flow_id"]
    _challenge_handler.flow_id = flow_id
    polled = client.get(f"/api/flows/{flow_id}")
    assert polled.json()["status"] == "COMPLETED"
    assert polled.json()["result"]["decision"] == "CHALLENGE"
    return flow_id


def test_a_challenge_decision_can_be_followed_up_and_reported(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_challenged_flow(monkeypatch, client, csrf)

    opened = client.post(f"/api/flows/{flow_id}/challenge", json={}, headers={"X-CSRF-Token": csrf})
    assert opened.status_code == 200
    assert opened.json()["attempt_id"] == "chgat_test"
    assert opened.json()["status"] == "PENDING"

    reported = client.post(
        f"/api/flows/{flow_id}/challenge/events",
        json={"result": "PASSED"},
        headers={"X-CSRF-Token": csrf},
    )
    assert reported.status_code == 200
    assert reported.json()["status"] == "PASSED"

    polled = client.get(f"/api/flows/{flow_id}")
    assert polled.json()["challenge"]["status"] == "PASSED"
    # The signed decision itself must be untouched by the followup.
    assert polled.json()["result"]["decision"] == "CHALLENGE"


def test_opening_a_challenge_requires_a_session_and_csrf(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_challenged_flow(monkeypatch, client, csrf)

    no_session = TestClient(app, client=LOCAL_CLIENT).post(f"/api/flows/{flow_id}/challenge", json={})
    assert no_session.status_code == 401

    no_csrf = client.post(f"/api/flows/{flow_id}/challenge", json={})
    assert no_csrf.status_code == 403


def test_opening_a_challenge_on_a_non_challenged_flow_is_refused(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/consents/number-verification":
            return httpx.Response(
                202,
                json={
                    "consent_id": "cns_allow",
                    "status": "PENDING",
                    "authorization_url": "https://consent.test/authorize?state=s",
                    "expires_at": "2026-01-01T00:05:00+00:00",
                    "chain_id": None,
                    "reason": None,
                },
            )
        if request.url.path == "/v1/consents/cns_allow":
            return httpx.Response(
                200,
                json={
                    "consent_id": "cns_allow",
                    "status": "AUTHORIZED",
                    "authorization_url": "https://consent.test/authorize?state=s",
                    "expires_at": "2026-01-01T00:05:00+00:00",
                    "chain_id": None,
                    "reason": None,
                },
            )
        if request.url.path == "/v1/consents/cns_allow/verify":
            return httpx.Response(
                200,
                json={
                    "decision": "ALLOW",
                    "planner": "greedy",
                    "chain_grade": None,
                    "confidence": 0.1,
                    "hypothesis": "h",
                    "reason": "r",
                    "chain_id": "chn_allow2",
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
    created = client.post("/api/flows", json={"phone_number": "+15551234567"}, headers={"X-CSRF-Token": csrf})
    flow_id = created.json()["flow_id"]
    client.get(f"/api/flows/{flow_id}")

    resp = client.post(f"/api/flows/{flow_id}/challenge", json={}, headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 409


def test_reporting_before_a_challenge_is_opened_is_404(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_challenged_flow(monkeypatch, client, csrf)

    resp = client.post(
        f"/api/flows/{flow_id}/challenge/events",
        json={"result": "PASSED"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 404


def test_an_outcome_can_be_reported_and_corrected(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_challenged_flow(monkeypatch, client, csrf)

    first = client.post(
        f"/api/flows/{flow_id}/outcomes",
        json={"dimension": "order_status", "value": "ACCEPTED"},
        headers={"X-CSRF-Token": csrf},
    )
    assert first.status_code == 200
    assert first.json()["value"] == "ACCEPTED"
    assert first.json()["supersedes_event_id"] is None

    corrected = client.post(
        f"/api/flows/{flow_id}/outcomes",
        json={"dimension": "order_status", "value": "CANCELLED"},
        headers={"X-CSRF-Token": csrf},
    )
    assert corrected.status_code == 200
    assert corrected.json()["value"] == "CANCELLED"
    assert corrected.json()["supersedes_event_id"] == first.json()["event_id"]

    polled = client.get(f"/api/flows/{flow_id}")
    assert polled.json()["outcomes"]["order_status"]["value"] == "CANCELLED"
    # A dimension never reported must not appear.
    assert "fraud_assessment" not in polled.json()["outcomes"]


def test_a_fraud_outcome_can_be_reported_with_a_basis(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_challenged_flow(monkeypatch, client, csrf)

    resp = client.post(
        f"/api/flows/{flow_id}/outcomes",
        json={"dimension": "fraud_assessment", "value": "CONFIRMED_FRAUD", "basis": "manual_investigation"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["basis"] == "manual_investigation"


def test_reporting_an_outcome_requires_a_session_and_csrf(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_challenged_flow(monkeypatch, client, csrf)

    no_session = TestClient(app, client=LOCAL_CLIENT).post(
        f"/api/flows/{flow_id}/outcomes", json={"dimension": "order_status", "value": "ACCEPTED"}
    )
    assert no_session.status_code == 401

    no_csrf = client.post(f"/api/flows/{flow_id}/outcomes", json={"dimension": "order_status", "value": "ACCEPTED"})
    assert no_csrf.status_code == 403


def test_an_unknown_outcome_dimension_is_rejected(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_challenged_flow(monkeypatch, client, csrf)

    resp = client.post(
        f"/api/flows/{flow_id}/outcomes",
        json={"dimension": "shipping_status", "value": "X"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 422


def test_capabilities_requires_a_session():
    client = _client()
    response = client.get("/api/capabilities")
    assert response.status_code == 401


def test_capabilities_lists_the_manifest_read_only():
    client = _client()
    _login(client)
    response = client.get("/api/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == 1
    assert len(body["capabilities"]) >= 6


def _session_handler(request: httpx.Request):
    if request.url.path == "/v1/consents/number-verification":
        return httpx.Response(
            202,
            json={
                "consent_id": "cns_session",
                "status": "PENDING",
                "authorization_url": "https://consent.test/authorize?state=s",
                "expires_at": "2026-01-01T00:05:00+00:00",
                "chain_id": None,
                "reason": None,
            },
        )
    if request.url.path == "/v1/consents/cns_session":
        return httpx.Response(
            200,
            json={
                "consent_id": "cns_session",
                "status": "AUTHORIZED",
                "authorization_url": "https://consent.test/authorize?state=s",
                "expires_at": "2026-01-01T00:05:00+00:00",
                "chain_id": None,
                "reason": None,
            },
        )
    if request.url.path == "/v1/consents/cns_session/verify":
        return httpx.Response(
            200,
            json={
                "decision": "ALLOW",
                "planner": "greedy",
                "chain_grade": "ATTESTED_FULL",
                "confidence": 0.05,
                "hypothesis": "legit",
                "reason": "r",
                "chain_id": "chn_session",
                "evidence_cost": 0.0,
                "latency_ms": 1,
                "evidence_steps": 1,
                "provider_sources": ["test"],
            },
        )
    if request.url.path == "/v1/sessions" and request.method == "POST":
        return httpx.Response(
            200,
            json={
                "session_id": "sess_test",
                "status": "ACTIVE",
                "phone_number": "+1***67",
                "reason": None,
                "created_at": "2026-01-01T00:00:00+00:00",
                "expires_at": "2026-01-01T00:02:00+00:00",
            },
        )
    if request.url.path == "/v1/sessions/sess_test" and request.method == "GET":
        status_value = _session_handler.current_status
        return httpx.Response(
            200,
            json={
                "session_id": "sess_test",
                "status": status_value,
                "phone_number": "+1***67",
                "reason": "SIM swap detected" if status_value == "REVOKED" else None,
                "created_at": "2026-01-01T00:00:00+00:00",
                "expires_at": "2026-01-01T00:02:00+00:00",
            },
        )
    if request.url.path == "/v1/sessions/sess_test/simulate-swap":
        _session_handler.current_status = "REVOKED"
        return httpx.Response(200, json={"status": "REVOKED"})
    raise AssertionError(f"unexpected call to {request.url.path}")


_session_handler.current_status = "ACTIVE"


def _make_allowed_flow(monkeypatch, client: TestClient, csrf: str) -> str:
    _session_handler.current_status = "ACTIVE"
    _patch_isnad(monkeypatch, _session_handler)
    created = client.post(
        "/api/flows",
        json={"phone_number": "+15551234567"},
        headers={"X-CSRF-Token": csrf},
    )
    flow_id = created.json()["flow_id"]
    polled = client.get(f"/api/flows/{flow_id}")
    assert polled.json()["status"] == "COMPLETED"
    assert polled.json()["result"]["decision"] == "ALLOW"
    return flow_id


def test_a_trust_session_can_be_opened_and_the_order_released(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_allowed_flow(monkeypatch, client, csrf)

    opened = client.post(f"/api/flows/{flow_id}/trust-session", json={}, headers={"X-CSRF-Token": csrf})
    assert opened.status_code == 200
    assert opened.json()["fulfillment_state"] == "HELD"

    released = client.post(f"/api/flows/{flow_id}/release-order", json={}, headers={"X-CSRF-Token": csrf})
    assert released.status_code == 200
    assert released.json()["fulfillment_state"] == "RELEASED"


def test_a_revoked_session_blocks_release(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_allowed_flow(monkeypatch, client, csrf)
    client.post(f"/api/flows/{flow_id}/trust-session", json={}, headers={"X-CSRF-Token": csrf})

    client.post(f"/api/flows/{flow_id}/simulate-swap", json={}, headers={"X-CSRF-Token": csrf})

    released = client.post(f"/api/flows/{flow_id}/release-order", json={}, headers={"X-CSRF-Token": csrf})
    assert released.status_code == 409
    polled = client.get(f"/api/flows/{flow_id}")
    assert polled.json()["session"]["fulfillment_state"] == "HELD"
    assert polled.json()["session"]["status"] == "REVOKED"


def test_release_without_an_open_session_is_404(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_allowed_flow(monkeypatch, client, csrf)
    resp = client.post(f"/api/flows/{flow_id}/release-order", json={}, headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 404


def test_repeated_release_after_success_is_a_no_op_not_a_double_release(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_allowed_flow(monkeypatch, client, csrf)
    client.post(f"/api/flows/{flow_id}/trust-session", json={}, headers={"X-CSRF-Token": csrf})

    first = client.post(f"/api/flows/{flow_id}/release-order", json={}, headers={"X-CSRF-Token": csrf})
    second = client.post(f"/api/flows/{flow_id}/release-order", json={}, headers={"X-CSRF-Token": csrf})
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["fulfillment_state"] == "RELEASED"


def test_trust_session_and_release_require_a_session_and_csrf(monkeypatch):
    client = _client()
    csrf = _login(client)
    flow_id = _make_allowed_flow(monkeypatch, client, csrf)

    no_session = TestClient(app, client=LOCAL_CLIENT).post(f"/api/flows/{flow_id}/trust-session", json={})
    assert no_session.status_code == 401

    no_csrf = client.post(f"/api/flows/{flow_id}/trust-session", json={})
    assert no_csrf.status_code == 403


# --- UI surfaces (static assertions, matching test_t6_receipt.py's own pattern) ---

_STATIC = Path(__file__).resolve().parents[1] / "demo" / "merchant_pilot" / "static"
INDEX_HTML = (_STATIC / "index.html").read_text(encoding="utf-8")
FLOW_HTML = (_STATIC / "flow.html").read_text(encoding="utf-8")
CAPABILITIES_HTML = (_STATIC / "capabilities.html").read_text(encoding="utf-8")


def test_the_checkout_form_offers_a_claimed_location_labelled_as_a_claim():
    """I11: the field must read as a customer/merchant CLAIM, never as an
    observed device location, and omitting it must state the consequence."""
    assert 'name="lat"' in INDEX_HTML
    assert 'name="lon"' in INDEX_HTML
    assert 'name="radius_m"' in INDEX_HTML
    assert "claim" in INDEX_HTML.lower()
    assert "location cannot be verified" in INDEX_HTML


def test_the_claim_is_all_or_nothing():
    """A latitude with no longitude is an incomplete claim, not a partial one."""
    assert "incomplete" in INDEX_HTML.lower()


def test_the_capabilities_page_separates_recorded_history_from_a_live_probe():
    """I10: a green past capture is not an uptime probe or a coverage claim."""
    assert "not a live probe" in CAPABILITIES_HTML
    assert "uptime" in CAPABILITIES_HTML
    assert "coverage" in CAPABILITIES_HTML
    # Rendered with textContent, never innerHTML: the manifest is an
    # operator-edited file and markup in it must not become markup here.
    assert "textContent" in CAPABILITIES_HTML


def test_the_capabilities_page_requires_a_session():
    client = _client()
    response = client.get("/capabilities", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_the_capabilities_page_renders_for_an_operator():
    client = _client()
    _login(client)
    response = client.get("/capabilities")
    assert response.status_code == 200
    assert "Provider readiness" in response.text


def test_the_session_panel_shows_every_state_distinctly():
    """I8: ACTIVE, REVOKED, EXPIRED, ENDED and unknown each render
    differently, and an unavailable lookup is never permission to proceed."""
    for state in ("ACTIVE", "REVOKED", "EXPIRED", "ENDED", "UNKNOWN"):
        assert f".session .state.{state}" in FLOW_HTML or f'"{state}"' in FLOW_HTML
    assert "not permission to proceed" in FLOW_HTML


def test_the_session_panel_is_labelled_a_simulator():
    assert "Simulator." in FLOW_HTML
    assert "durable across a restart" in FLOW_HTML
    assert "not transactional enforcement" in FLOW_HTML


def test_a_release_cannot_be_undone_by_a_later_revocation_in_the_copy():
    assert "cannot undo a release that already happened" in FLOW_HTML


def test_the_outcomes_panel_preserves_an_in_progress_selection_across_polls():
    """P5 known gap #4: the panel re-renders every poll tick, which used to
    reset a half-made selection under the operator's cursor."""
    assert "inProgress" in FLOW_HTML
    assert "Restore whatever the operator had selected" in FLOW_HTML


def test_logout_clears_the_session():
    client = _client()
    _login(client)

    client.post("/logout", follow_redirects=False)

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
