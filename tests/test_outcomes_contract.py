"""P5 — collect outcomes before calibrating scores.

Merchants report what actually happened (order status, fraud assessment) on
any owned chain, including ALLOW/DECLINE — there is no CHALLENGE gate here,
unlike P3. Corrections are appended, never rewritten: exactly one current
event per (owner, chain, dimension) at a time, with old events superseded in
place. None of this touches the signed Verdict.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.chain.models import Verdict
from app.db import store
from app.domain.enums import ChainGrade, Decision
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}
OTHER_AUTH = {"Authorization": "Bearer other-merchant-key"}
_key_counter = iter(range(1_000_000))


def _fresh_headers(base: dict) -> dict:
    return {**base, "Idempotency-Key": f"k-auto-{next(_key_counter)}"}


@pytest.fixture(autouse=True)
def _extra_merchant_key(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "merchant_api_keys", "demo-merchant-key,other-merchant-key")


@pytest.fixture(autouse=True)
def _as_the_merchant():
    from app.events import current_owner
    from app.ownership import owner_hash

    token = current_owner.set(owner_hash("demo-merchant-key"))
    yield
    current_owner.reset(token)


@pytest.fixture(autouse=True)
def _reset_limiters():
    """This file fires many requests against a couple of fixed keys; do not
    leak that traffic into later tests' own rate-limit assertions."""
    from app.api import rate_limit

    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()
    yield
    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()


def _seed(chain_id: str, decision: Decision = Decision.ALLOW):
    verdict = Verdict(
        decision=decision,
        chain_grade=ChainGrade.ATTESTED_PARTIAL,
        confidence=0.1,
        hypothesis="legit",
        reason="",
        chain_id=chain_id,
    )
    return store.save(verdict)


def _report(chain_id: str, body: dict, headers: dict | None = None):
    return client.post(
        f"/v1/chains/{chain_id}/outcomes", json=body, headers=headers or _fresh_headers(AUTH)
    )


def _get(chain_id: str, headers: dict | None = None):
    return client.get(f"/v1/chains/{chain_id}/outcomes", headers=headers or {"Authorization": AUTH["Authorization"]})


ORDER_BODY = {"dimension": "order_status", "value": "FULFILLED", "occurred_at": "2026-01-01T00:00:00+00:00"}
FRAUD_BODY = {
    "dimension": "fraud_assessment",
    "value": "CONFIRMED_FRAUD",
    "basis": "manual_investigation",
    "occurred_at": "2026-01-01T00:00:00+00:00",
}


# --- no decision gate ----------------------------------------------------------


def test_an_outcome_can_be_reported_on_an_allow_chain():
    _seed("chn_o1", decision=Decision.ALLOW)
    resp = _report("chn_o1", ORDER_BODY)
    assert resp.status_code == 201
    assert resp.json()["value"] == "FULFILLED"


def test_an_outcome_can_be_reported_on_a_decline_chain():
    _seed("chn_o2", decision=Decision.DECLINE)
    resp = _report("chn_o2", ORDER_BODY)
    assert resp.status_code == 201


def test_a_missing_chain_is_404():
    resp = _report("chn_does_not_exist", ORDER_BODY)
    assert resp.status_code == 404


def test_a_foreign_owner_cannot_report_or_read():
    _seed("chn_o3")
    assert _report("chn_o3", ORDER_BODY, headers=_fresh_headers(OTHER_AUTH)).status_code == 404
    assert _get("chn_o3", headers={"Authorization": OTHER_AUTH["Authorization"]}).status_code == 404


def test_reporting_requires_authentication():
    _seed("chn_o4")
    resp = client.post(
        "/v1/chains/chn_o4/outcomes", json=ORDER_BODY, headers={"Idempotency-Key": "k"}
    )
    assert resp.status_code == 401


def test_reporting_requires_an_idempotency_key():
    _seed("chn_o5")
    resp = client.post(
        "/v1/chains/chn_o5/outcomes", json=ORDER_BODY, headers={"Authorization": AUTH["Authorization"]}
    )
    assert resp.status_code == 422


# --- schema: discriminated union, no free text, basis rules ---------------------


def test_a_free_text_field_is_rejected():
    _seed("chn_o6")
    resp = _report("chn_o6", {**ORDER_BODY, "notes": "customer called to complain"})
    assert resp.status_code == 422


def test_an_unknown_dimension_is_rejected():
    _seed("chn_o7")
    resp = _report("chn_o7", {"dimension": "shipping_carrier", "value": "UPS", "occurred_at": "2026-01-01T00:00:00+00:00"})
    assert resp.status_code == 422


def test_confirmed_fraud_requires_a_basis():
    _seed("chn_o8")
    resp = _report(
        "chn_o8",
        {"dimension": "fraud_assessment", "value": "CONFIRMED_FRAUD", "occurred_at": "2026-01-01T00:00:00+00:00"},
    )
    assert resp.status_code == 422


def test_inconclusive_must_not_carry_a_basis():
    _seed("chn_o9")
    resp = _report(
        "chn_o9",
        {
            "dimension": "fraud_assessment",
            "value": "INCONCLUSIVE",
            "basis": "manual_investigation",
            "occurred_at": "2026-01-01T00:00:00+00:00",
        },
    )
    assert resp.status_code == 422


def test_a_naive_timestamp_is_rejected():
    _seed("chn_o10")
    resp = _report("chn_o10", {**ORDER_BODY, "occurred_at": "2026-01-01T00:00:00"})
    assert resp.status_code == 422


def test_a_future_timestamp_beyond_tolerance_is_rejected():
    _seed("chn_o11")
    resp = _report("chn_o11", {**ORDER_BODY, "occurred_at": "2099-01-01T00:00:00+00:00"})
    assert resp.status_code == 422


# --- supersession: exactly one current event per dimension ----------------------


def test_a_second_report_without_supersedes_is_a_conflict():
    _seed("chn_o12")
    first = _report("chn_o12", ORDER_BODY)
    assert first.status_code == 201
    second = _report("chn_o12", {**ORDER_BODY, "value": "CANCELLED"})
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "dimension_already_labelled"


def test_a_correction_naming_the_current_head_succeeds():
    _seed("chn_o13")
    first = _report("chn_o13", ORDER_BODY).json()
    second = _report("chn_o13", {**ORDER_BODY, "value": "CANCELLED", "supersedes_event_id": first["event_id"]})
    assert second.status_code == 201
    current = _get("chn_o13").json()["current"]
    assert current["order_status"]["value"] == "CANCELLED"
    assert current["order_status"]["event_id"] == second.json()["event_id"]


def test_correcting_an_already_superseded_event_is_a_conflict():
    _seed("chn_o14")
    first = _report("chn_o14", ORDER_BODY).json()
    _report("chn_o14", {**ORDER_BODY, "value": "CANCELLED", "supersedes_event_id": first["event_id"]})
    stale = _report("chn_o14", {**ORDER_BODY, "value": "ACCEPTED", "supersedes_event_id": first["event_id"]})
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "supersede_target_not_found"


def test_superseding_a_foreign_chains_event_is_a_conflict():
    _seed("chn_o15a")
    _seed("chn_o15b")
    first = _report("chn_o15a", ORDER_BODY).json()
    resp = _report("chn_o15b", {**ORDER_BODY, "supersedes_event_id": first["event_id"]})
    assert resp.status_code == 409


def test_the_two_dimensions_are_independent():
    _seed("chn_o16")
    _report("chn_o16", ORDER_BODY)
    fraud = _report("chn_o16", FRAUD_BODY)
    assert fraud.status_code == 201
    current = _get("chn_o16").json()["current"]
    assert set(current.keys()) == {"order_status", "fraud_assessment"}


def test_a_passed_challenge_does_not_fill_in_a_fraud_label():
    """P3's own dimension is derived, not reported through this endpoint —
    reporting order_status must never create a fraud_assessment row."""
    _seed("chn_o17")
    _report("chn_o17", ORDER_BODY)
    current = _get("chn_o17").json()["current"]
    assert "fraud_assessment" not in current


# --- idempotency -----------------------------------------------------------------


def test_retrying_the_same_key_and_body_replays():
    _seed("chn_o18")
    key = _fresh_headers(AUTH)
    first = _report("chn_o18", ORDER_BODY, headers=key)
    second = _report("chn_o18", ORDER_BODY, headers=key)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()


def test_reusing_a_key_with_a_different_body_is_a_conflict():
    _seed("chn_o19")
    key = _fresh_headers(AUTH)
    _report("chn_o19", ORDER_BODY, headers=key)
    resp = _report("chn_o19", {**ORDER_BODY, "value": "CANCELLED"}, headers=key)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "idempotency_key_reused"


# --- no leak / signed-payload immutability --------------------------------------


def test_reporting_never_changes_the_signed_chain_record():
    chain_id = "chn_o20"
    original = _seed(chain_id)
    _report(chain_id, ORDER_BODY)
    _report(chain_id, FRAUD_BODY)
    reread = store.get_record(chain_id)
    assert reread.verdict_json == original.verdict_json
    assert reread.signature == original.signature
    assert reread.signed_at == original.signed_at


def test_the_public_receipt_is_unaffected_by_outcome_reports():
    chain_id = "chn_o21"
    _seed(chain_id)
    before = client.get(f"/r/{chain_id}")
    _report(chain_id, ORDER_BODY)
    _report(chain_id, FRAUD_BODY)
    after = client.get(f"/r/{chain_id}")
    assert before.text == after.text
