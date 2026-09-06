"""Regression tests for the 6 September 2026 code review (docs/PHASE2_HANDOFF.md
§9, findings R1-R7). Adapted from docs/reviews/sonnet_review_regressions.py:
`add_flow()` now takes an explicit `owner_session_id` (R1 added that field to
`FlowRecord`), and assertions are otherwise unchanged from the review's own
probes.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

os.environ.setdefault("ISNAD_MERCHANT_API_KEY", "review-merchant-key")
os.environ.setdefault("PILOT_OPERATOR_USERNAME", "review-operator")
os.environ.setdefault("PILOT_OPERATOR_PASSWORD", "review-password")

import httpx
import pytest
from starlette.testclient import TestClient

import demo.merchant_pilot.app as pilot
from app.consent import ConsentStore
from app.domain.schemas import VerificationRequest
from app.providers.nac import NacProvider


def client_for(session) -> TestClient:
    c = TestClient(pilot.app, client=("127.0.0.1", 51000), raise_server_exceptions=False)
    c.cookies.set(pilot.SESSION_COOKIE, session.session_id)
    return c


def add_flow(owner_session_id: str, **overrides):
    now = datetime.now(UTC)
    kwargs = {
        "flow_id": "flw_review",
        "owner_session_id": owner_session_id,
        "consent_id": "cns_review",
        "phone_number": "+99999991000",
        "context_event": "checkout",
        "authorization_url": "https://operator.test/authorize?state=review",
        "qr_svg": "<svg/>",
        "created_at": now,
        "expires_at": now + timedelta(minutes=5),
        "status": "COMPLETED",
        "result": {"chain_id": "chn_review", "decision": "CHALLENGE"},
    }
    kwargs.update(overrides)
    f = pilot.FlowRecord(**kwargs)
    pilot.flows.add(f)
    return f


def upstream(monkeypatch, handler) -> None:
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("base_url", None)
        kwargs.pop("timeout", None)
        return real(transport=httpx.MockTransport(handler), base_url="https://isnad.test")

    monkeypatch.setattr(pilot.httpx, "AsyncClient", factory)


def test_review_foreign_operator_session_cannot_read_flow(monkeypatch):
    a = pilot.sessions.create()
    b = pilot.sessions.create()

    def handler(req):
        return httpx.Response(
            202,
            json={
                "consent_id": "cns_foreign",
                "status": "PENDING",
                "authorization_url": "https://operator.test/authorize?state=s",
                "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            },
        )

    upstream(monkeypatch, handler)
    ca, cb = client_for(a), client_for(b)
    created = ca.post(
        "/api/flows", headers={"X-CSRF-Token": a.csrf_token}, json={"phone_number": "+99999991000"}
    )
    assert created.status_code == 200
    foreign = cb.get("/flow/" + created.json()["flow_id"])
    assert foreign.status_code == 404, f"foreign session received {foreign.status_code}"


@pytest.mark.asyncio
async def test_review_lost_verification_response_recovers_cached_completion(monkeypatch):
    session = pilot.sessions.create()
    flow = add_flow(session.session_id, status="PENDING", result=None)
    calls = []
    completed = False

    def handler(req):
        nonlocal completed
        calls.append(req.method)
        if req.method == "GET":
            return httpx.Response(200, json={"status": "COMPLETED" if completed else "AUTHORIZED"})
        if not completed:
            completed = True
            raise httpx.ReadError("response lost after upstream committed", request=req)
        return httpx.Response(200, json={"chain_id": "chn_recovered", "decision": "CHALLENGE"})

    upstream(monkeypatch, handler)
    await pilot._poll_and_maybe_complete(flow)
    await pilot._poll_and_maybe_complete(flow)
    assert flow.result is not None, f"status={flow.status}, result={flow.result}, requests={calls}"


def test_review_harness_read_enforces_flow_retention():
    session = pilot.sessions.create()
    flow = add_flow(
        session.session_id, created_at=datetime.now(UTC) - timedelta(seconds=pilot.FLOW_RETENTION_SECONDS + 1)
    )
    resp = client_for(session).get("/api/flows/" + flow.flow_id)
    assert resp.status_code == 404, f"expired retained flow still returned {resp.status_code}"


def test_review_consent_owned_read_enforces_terminal_retention(monkeypatch):
    now = datetime.now(UTC)
    store = ConsentStore(terminal_retention_seconds=1)
    record = store.create(
        VerificationRequest(phone_number="+99999991000"), "key", "https://merchant.test/cb", 300
    )
    store.fail(record, "done")
    import app.consent as cm

    monkeypatch.setattr(cm, "_now", lambda: now + timedelta(seconds=10))
    assert store.owned(record.consent_id, "key") is None, (
        "terminal result retained beyond configured TTL on reads"
    )


@pytest.mark.asyncio
async def test_review_sdk_exchange_rejects_unvalidated_access_token():
    provider = object.__new__(NacProvider)
    provider.client = SimpleNamespace(
        number_verification=SimpleNamespace(
            exchange_code_for_token=lambda code, redirect_uri: {"access_token": "unvalidated"}
        )
    )
    with pytest.raises(RuntimeError):
        await provider.exchange_number_verification_code(
            "code", "https://merchant.test/cb", "expected-nonce"
        )


def test_review_retry_reuses_exact_outcome_body(monkeypatch):
    session = pilot.sessions.create()
    flow = add_flow(session.session_id)
    client = client_for(session)
    saved = []

    def handler(req):
        body = json.loads(req.content)
        key = req.headers["idempotency-key"]
        saved.append((key, body))
        if len(saved) == 1:
            raise httpx.ReadError("response lost after upstream commit", request=req)
        if saved[0] != saved[-1]:
            return httpx.Response(409, json={"detail": {"code": "idempotency_key_reused"}})
        return httpx.Response(201, json={"event_id": "mout_review", **body})

    upstream(monkeypatch, handler)
    body = {"dimension": "order_status", "value": "FULFILLED"}
    headers = {"X-CSRF-Token": session.csrf_token}
    client.post("/api/flows/" + flow.flow_id + "/outcomes", json=body, headers=headers)
    retried = client.post("/api/flows/" + flow.flow_id + "/outcomes", json=body, headers=headers)
    assert retried.status_code == 200, (
        f"retry returned {retried.status_code}; same_key={saved[0][0] == saved[1][0]}, same_body={saved[0][1] == saved[1][1]}"
    )


def test_review_invalid_context_returns_422_instead_of_500():
    session = pilot.sessions.create()
    c = client_for(session)
    response = c.post(
        "/api/flows",
        headers={"X-CSRF-Token": session.csrf_token},
        json={"phone_number": "+99999991000", "event": "not_an_event", "account_age_days": -1},
    )
    assert response.status_code == 422, f"invalid context produced {response.status_code}"
