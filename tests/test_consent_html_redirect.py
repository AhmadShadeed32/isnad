"""P4a step 8 — a browser-preferring callback gets a generic HTML redirect.

The subscriber's phone browser navigates to the provider callback URL
directly; returning it a raw JSON blob (or, worse, an error page naming the
provider/consent state) is neither useful to them nor safe to leak into their
own browser history. An API/script client (curl, scripts/handset_validation.py)
must keep getting the existing JSON contract untouched.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import routes_consent
from app.chain.models import EvidenceLink
from app.domain.enums import API_LABEL, Action, Result
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}
BROWSER_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"


class FakeConsentProvider:
    async def begin_number_verification(self, phone_number, redirect_uri, state, nonce):
        return f"https://consent.test/authorize?state={state}"

    async def exchange_number_verification_code(self, code, redirect_uri, nonce):
        return "opaque-token-never-returned"

    async def gather(self, action, request):
        return EvidenceLink(
            step=0,
            action=action,
            api=API_LABEL[action],
            result=Result.PASS if action == Action.NUMBER_VERIFY else Result.INFO,
            signal="NUMBER_MATCH" if action == Action.NUMBER_VERIFY else "EVIDENCE_UNAVAILABLE",
            detail="test",
            source="test",
            latency_ms=1,
        )


def _patched(monkeypatch) -> FakeConsentProvider:
    provider = FakeConsentProvider()

    def get_provider(token=None):
        provider.number_verification_token = token
        return provider

    monkeypatch.setattr(routes_consent, "get_live_provider", get_provider)
    return provider


def _start() -> tuple[str, str]:
    response = client.post(
        "/v1/consents/number-verification",
        headers=AUTH,
        json={"phone_number": "+99999991000", "context": {"event": "signup"}},
    )
    body = response.json()
    return body["consent_id"], body["authorization_url"].split("state=", 1)[1]


def test_a_browser_preferring_callback_is_redirected_to_the_generic_page(monkeypatch):
    _patched(monkeypatch)
    _, state = _start()

    response = client.get(
        "/v1/consents/number-verification/callback",
        params={"state": state, "code": "operator-code"},
        headers={"Accept": BROWSER_ACCEPT},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/consent/complete"
    assert response.headers["vary"] == "Accept"
    assert response.headers["cache-control"] == "no-store"
    body_text = response.text
    for leak in ("operator-code", state, "opaque-token", "AUTHORIZED"):
        assert leak not in body_text


def test_a_browser_preferring_callback_is_redirected_even_when_denied(monkeypatch):
    _patched(monkeypatch)
    _, state = _start()

    response = client.get(
        "/v1/consents/number-verification/callback",
        params={"state": state, "error": "access_denied"},
        headers={"Accept": BROWSER_ACCEPT},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/consent/complete"
    assert "access_denied" not in response.text


def test_a_browser_preferring_callback_is_redirected_even_on_an_unknown_state(monkeypatch):
    response = client.get(
        "/v1/consents/number-verification/callback",
        params={"state": "not-a-real-state", "code": "x"},
        headers={"Accept": BROWSER_ACCEPT},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/consent/complete"


def test_a_script_client_with_no_accept_header_still_gets_json(monkeypatch):
    _patched(monkeypatch)
    _, state = _start()

    response = client.get(
        "/v1/consents/number-verification/callback",
        params={"state": state, "code": "operator-code"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "AUTHORIZED"


def test_a_wildcard_only_accept_keeps_json(monkeypatch):
    _patched(monkeypatch)
    _, state = _start()

    response = client.get(
        "/v1/consents/number-verification/callback",
        params={"state": state, "code": "operator-code"},
        headers={"Accept": "*/*"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "AUTHORIZED"


def test_a_tied_preference_keeps_json(monkeypatch):
    _patched(monkeypatch)
    _, state = _start()

    response = client.get(
        "/v1/consents/number-verification/callback",
        params={"state": state, "code": "operator-code"},
        headers={"Accept": "text/html;q=0.5,application/json;q=0.5"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "AUTHORIZED"


def test_the_completion_page_is_served_and_carries_no_dynamic_state():
    response = client.get("/consent/complete")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "return to the merchant" in response.text.lower()
