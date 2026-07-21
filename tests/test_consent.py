from __future__ import annotations

from app.api import routes_consent
from app.chain.models import EvidenceLink
from app.domain.enums import API_LABEL, Action, Result
from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


class FakeConsentProvider:
    def __init__(self) -> None:
        self.received_tokens = []

    async def begin_number_verification(self, phone_number, redirect_uri, state):
        assert phone_number == "+99999991000"
        return f"https://consent.test/authorize?state={state}"

    async def exchange_number_verification_code(self, code, redirect_uri):
        assert code == "operator-code"
        return "opaque-token-never-returned"

    async def gather(self, action, request):
        self.received_tokens.append(getattr(self, "number_verification_token", None))
        return EvidenceLink(
            step=0,
            action=action,
            api=API_LABEL[action],
            result=Result.PASS if action == Action.NUMBER_VERIFY else Result.INFO,
            signal="NUMBER_MATCH" if action == Action.NUMBER_VERIFY else "EVIDENCE_UNAVAILABLE",
            detail="network number matches the provided number"
            if action == Action.NUMBER_VERIFY
            else "test provider has no additional evidence",
            source="test",
            latency_ms=1,
        )


def test_number_verification_consent_callback_and_resume(monkeypatch):
    provider = FakeConsentProvider()

    def get_provider(token=None):
        provider.number_verification_token = token
        return provider

    monkeypatch.setattr(routes_consent, "get_live_provider", get_provider)
    response = client.post(
        "/v1/consents/number-verification",
        headers=AUTH,
        json={
            "phone_number": "+99999991000",
            "context": {"event": "signup", "account_age_days": 0},
        },
    )

    assert response.status_code == 202
    started = response.json()
    assert started["status"] == "PENDING"
    assert "opaque-token" not in response.text
    consent_id = started["consent_id"]
    state = started["authorization_url"].split("state=", 1)[1]

    callback = client.get(
        "/v1/consents/number-verification/callback",
        params={"state": state, "code": "operator-code"},
    )
    assert callback.status_code == 200
    assert callback.json()["status"] == "AUTHORIZED"
    assert "opaque-token" not in callback.text

    completed = client.post(f"/v1/consents/{consent_id}/verify", headers=AUTH)
    assert completed.status_code == 200
    assert completed.json()["chain_id"].startswith("chn_")
    assert "opaque-token-never-returned" in provider.received_tokens

    status_response = client.get(f"/v1/consents/{consent_id}", headers=AUTH)
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "COMPLETED"
    assert "opaque-token" not in status_response.text


def test_number_verification_consent_rejects_unknown_state():
    response = client.get(
        "/v1/consents/number-verification/callback",
        params={"state": "not-a-real-state", "code": "operator-code"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "consent_not_found"
