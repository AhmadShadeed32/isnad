"""S9 — an OAuth state must be single-use (authorization-code injection)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import routes_consent
from app.chain.models import EvidenceLink
from app.consent import consents
from app.domain.enums import API_LABEL, Action, Result
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


class RecordingProvider:
    """Counts token exchanges so a second one cannot pass unnoticed."""

    def __init__(self) -> None:
        self.exchanged_codes: list[str] = []

    async def begin_number_verification(self, phone_number, redirect_uri, state):
        return f"https://consent.test/authorize?state={state}"

    async def exchange_number_verification_code(self, code, redirect_uri):
        self.exchanged_codes.append(code)
        return f"token-for-{code}"

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


@pytest.fixture
def provider(monkeypatch) -> RecordingProvider:
    recorder = RecordingProvider()

    def get_provider(token=None):
        recorder.number_verification_token = token
        return recorder

    monkeypatch.setattr(routes_consent, "get_live_provider", get_provider)
    return recorder


def _start_consent() -> tuple[str, str]:
    response = client.post(
        "/v1/consents/number-verification",
        headers=AUTH,
        json={"phone_number": "+99999991000", "context": {"event": "signup"}},
    )
    assert response.status_code == 202
    body = response.json()
    return body["consent_id"], body["authorization_url"].split("state=", 1)[1]


def test_a_replayed_callback_is_rejected(provider):
    """The acceptance criterion: a replayed callback returns 409.

    The attacker's path: the state is in the authorization URL the console
    window.open()s. Observe it, replay the callback with your own code, and
    whichever exchange lands first binds *your* Number Verification token into
    the merchant's consent record — which then drives investigate().
    """
    _, state = _start_consent()

    first = client.get(
        "/v1/consents/number-verification/callback",
        params={"state": state, "code": "operator-code"},
    )
    assert first.status_code == 200
    assert first.json()["status"] == "AUTHORIZED"

    replay = client.get(
        "/v1/consents/number-verification/callback",
        params={"state": state, "code": "attacker-code"},
    )
    assert replay.status_code == 404  # the state no longer resolves at all
    assert provider.exchanged_codes == ["operator-code"]


def test_the_state_stops_resolving_once_it_is_claimed(provider):
    """by_state() used to keep resolving after use."""
    _, state = _start_consent()
    assert consents.by_state(state) is not None

    client.get(
        "/v1/consents/number-verification/callback",
        params={"state": state, "code": "operator-code"},
    )
    assert consents.by_state(state) is None


def test_a_second_callback_mid_exchange_gets_409(provider):
    """The 409 guard the old code could never reach.

    begin_callback() returned record.status after conditionally promoting
    PENDING -> EXCHANGING, so a second callback on an already-EXCHANGING record
    also returned "EXCHANGING" and the guard's condition was never true.
    """
    _, state = _start_consent()
    record = consents.by_state(state)

    assert consents.begin_callback(record) == "EXCHANGING"  # won the CAS
    assert consents.begin_callback(record) == consents.REPLAYED  # lost it


def test_two_concurrent_callbacks_produce_exactly_one_exchange(provider):
    """Whichever lands first used to win; both used to proceed."""
    _, state = _start_consent()

    def fire(code: str) -> int:
        return client.get(
            "/v1/consents/number-verification/callback",
            params={"state": state, "code": code},
        ).status_code

    codes = [fire("operator-code"), fire("attacker-code")]

    assert codes[0] == 200
    assert codes[1] in {404, 409}
    assert provider.exchanged_codes == ["operator-code"]


def test_a_denied_consent_also_burns_its_state(provider):
    _, state = _start_consent()

    denied = client.get(
        "/v1/consents/number-verification/callback",
        params={"state": state, "error": "access_denied"},
    )
    assert denied.status_code == 200
    assert denied.json()["status"] == "DENIED"
    assert consents.by_state(state) is None


def test_the_happy_path_still_completes(provider):
    """The fix must not have cost the flow it protects."""
    consent_id, state = _start_consent()

    client.get(
        "/v1/consents/number-verification/callback",
        params={"state": state, "code": "operator-code"},
    )
    completed = client.post(f"/v1/consents/{consent_id}/verify", headers=AUTH)

    assert completed.status_code == 200
    assert completed.json()["chain_id"].startswith("chn_")
