"""P3 — finish CHALLENGE without rewriting its receipt.

A merchant that gets CHALLENGE can report what happened when they followed up
(manual review, called the customer back, whatever). None of that may touch
the signed Verdict: the original decision, payload and signature must read
back byte-identical no matter how many followups accumulate against a chain.
"""

from __future__ import annotations

import time

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
    """A distinct Idempotency-Key per call, so tests that don't care about
    idempotency itself don't accidentally collide across different targets."""
    return {**base, "Idempotency-Key": f"k-auto-{next(_key_counter)}"}


@pytest.fixture(autouse=True)
def _extra_merchant_key(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "merchant_api_keys", "demo-merchant-key,other-merchant-key")


@pytest.fixture(autouse=True)
def _as_the_merchant():
    """Direct store.save() calls below need a caller set, same as S5's tests."""
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


def _seed(chain_id: str, decision: Decision = Decision.CHALLENGE):
    verdict = Verdict(
        decision=decision,
        chain_grade=ChainGrade.DEGRADED,
        confidence=0.4,
        hypothesis="account_takeover",
        reason="",
        chain_id=chain_id,
    )
    return store.save(verdict)


def _create(chain_id: str, headers: dict | None = None, **kw):
    return client.post(
        f"/v1/chains/{chain_id}/challenges",
        json={"method": "manual_review", **kw},
        headers=headers or _fresh_headers(AUTH),
    )


def _report(chain_id: str, attempt_id: str, result: str, headers: dict | None = None):
    return client.post(
        f"/v1/chains/{chain_id}/challenges/{attempt_id}/events",
        json={"result": result},
        headers=headers or _fresh_headers(AUTH),
    )


def _timeline(chain_id: str, headers: dict | None = None):
    return client.get(f"/v1/chains/{chain_id}/challenges", headers=headers or {"Authorization": AUTH["Authorization"]})


# --- creation ----------------------------------------------------------------


def test_a_challenge_attempt_can_be_created_on_a_challenged_chain():
    _seed("chn_c1")
    resp = _create("chn_c1")
    assert resp.status_code == 201
    body = resp.json()
    assert body["chain_id"] == "chn_c1"
    assert body["status"] == "PENDING"
    assert body["method"] == "manual_review"
    assert body["attempt_id"]


def test_creating_a_challenge_on_a_non_challenged_chain_is_refused():
    _seed("chn_c2", decision=Decision.ALLOW)
    resp = _create("chn_c2")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "not_challenged"


def test_creating_a_challenge_on_a_missing_chain_is_404():
    resp = _create("chn_does_not_exist")
    assert resp.status_code == 404


def test_creating_a_challenge_requires_authentication():
    _seed("chn_c3")
    resp = client.post(
        "/v1/chains/chn_c3/challenges", json={"method": "manual_review"}, headers={"Idempotency-Key": "k"}
    )
    assert resp.status_code == 401


def test_creating_a_challenge_requires_an_idempotency_key():
    _seed("chn_c4")
    resp = client.post(
        "/v1/chains/chn_c4/challenges",
        json={"method": "manual_review"},
        headers={"Authorization": AUTH["Authorization"]},
    )
    assert resp.status_code == 422


def test_a_free_text_field_on_the_create_body_is_rejected():
    _seed("chn_c5")
    resp = client.post(
        "/v1/chains/chn_c5/challenges",
        json={"method": "manual_review", "notes": "called the customer, seemed fine"},
        headers=AUTH,
    )
    assert resp.status_code == 422


# --- ownership isolation -------------------------------------------------------


def test_a_foreign_key_cannot_create_a_challenge_on_someone_elses_chain():
    _seed("chn_c6")
    resp = _create("chn_c6", headers=_fresh_headers(OTHER_AUTH))
    assert resp.status_code == 404


def test_a_foreign_key_cannot_report_against_someone_elses_attempt():
    _seed("chn_c7")
    attempt_id = _create("chn_c7").json()["attempt_id"]
    resp = _report("chn_c7", attempt_id, "PASSED", headers={**OTHER_AUTH, "Idempotency-Key": "k-other"})
    assert resp.status_code == 404


def test_a_foreign_key_cannot_read_someone_elses_timeline():
    _seed("chn_c8")
    _create("chn_c8")
    resp = _timeline("chn_c8", headers={"Authorization": OTHER_AUTH["Authorization"]})
    assert resp.status_code == 404


# --- reporting a result / transitions -----------------------------------------


@pytest.mark.parametrize("result", ["PASSED", "FAILED", "ABANDONED"])
def test_reporting_each_terminal_result(result):
    chain_id = f"chn_result_{result.lower()}"
    _seed(chain_id)
    attempt_id = _create(chain_id).json()["attempt_id"]
    resp = _report(chain_id, attempt_id, result, headers={**AUTH, "Idempotency-Key": f"k-{result}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == result
    assert body["result"] == result


def test_reporting_against_a_missing_attempt_is_404():
    _seed("chn_c9")
    resp = _report("chn_c9", "chgat_does_not_exist", "PASSED")
    assert resp.status_code == 404


def test_reporting_an_invalid_result_value_is_rejected():
    _seed("chn_c10")
    attempt_id = _create("chn_c10").json()["attempt_id"]
    resp = client.post(
        f"/v1/chains/chn_c10/challenges/{attempt_id}/events",
        json={"result": "MAYBE"},
        headers=AUTH,
    )
    assert resp.status_code == 422


def test_a_second_conflicting_result_against_a_resolved_attempt_is_409():
    _seed("chn_c11")
    attempt_id = _create("chn_c11").json()["attempt_id"]
    first = _report("chn_c11", attempt_id, "PASSED", headers={**AUTH, "Idempotency-Key": "k-first"})
    assert first.status_code == 200
    second = _report("chn_c11", attempt_id, "FAILED", headers={**AUTH, "Idempotency-Key": "k-second"})
    assert second.status_code == 409


def test_a_free_text_field_on_the_event_body_is_rejected():
    _seed("chn_c12")
    attempt_id = _create("chn_c12").json()["attempt_id"]
    resp = client.post(
        f"/v1/chains/chn_c12/challenges/{attempt_id}/events",
        json={"result": "PASSED", "note": "spoke to the cardholder"},
        headers=AUTH,
    )
    assert resp.status_code == 422


# --- idempotency ---------------------------------------------------------------


def test_retrying_the_same_key_and_body_replays_the_same_attempt():
    _seed("chn_c13")
    key = {"Authorization": AUTH["Authorization"], "Idempotency-Key": "k-replay"}
    first = _create("chn_c13", headers=key)
    second = _create("chn_c13", headers=key)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()


def test_reusing_a_key_against_a_different_chain_is_a_conflict():
    _seed("chn_c14a")
    _seed("chn_c14b")
    key = {"Authorization": AUTH["Authorization"], "Idempotency-Key": "k-cross-chain"}
    first = _create("chn_c14a", headers=key)
    assert first.status_code == 201
    second = _create("chn_c14b", headers=key)
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "idempotency_key_reused"


def test_reusing_a_key_with_a_different_body_is_a_conflict():
    _seed("chn_c15")
    attempt_id = _create("chn_c15", headers={**AUTH, "Idempotency-Key": "k-body"}).json()["attempt_id"]
    key = {"Authorization": AUTH["Authorization"], "Idempotency-Key": "k-body-2"}
    first = _report("chn_c15", attempt_id, "PASSED", headers=key)
    assert first.status_code == 200
    second = _report("chn_c15", attempt_id, "FAILED", headers=key)
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "idempotency_key_reused"


def test_the_idempotency_record_survives_a_fresh_database_session():
    """Not an in-memory cache (P4a's rule for /v1/verify explicitly does not
    apply here): a brand-new SessionLocal() must see the same replay, proving
    the record lives in the database and not in process memory."""
    _seed("chn_c16")
    key = {"Authorization": AUTH["Authorization"], "Idempotency-Key": "k-durable"}
    first = _create("chn_c16", headers=key)

    from app.db.database import SessionLocal
    from app.db.models import IdempotencyRecordRow
    from app.ownership import owner_hash

    with SessionLocal() as session:
        row = session.get(
            IdempotencyRecordRow, (owner_hash("demo-merchant-key"), "challenge.create", "k-durable")
        )
        assert row is not None

    second = _create("chn_c16", headers=key)
    assert second.json() == first.json()


# --- expiry ----------------------------------------------------------------------


def test_an_expired_attempt_cannot_be_reported_against(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "challenge_attempt_ttl_seconds", 0)
    _seed("chn_c17")
    attempt_id = _create("chn_c17").json()["attempt_id"]
    time.sleep(0.01)
    resp = _report("chn_c17", attempt_id, "PASSED", headers={**AUTH, "Idempotency-Key": "k-expired"})
    assert resp.status_code == 409
    timeline = _timeline("chn_c17").json()
    assert timeline["attempts"][0]["status"] == "EXPIRED"


# --- timeline / signed-payload immutability -------------------------------------


def test_the_timeline_lists_attempts_and_their_events():
    _seed("chn_c18")
    attempt_id = _create("chn_c18").json()["attempt_id"]
    _report("chn_c18", attempt_id, "PASSED")
    body = _timeline("chn_c18").json()
    assert body["chain_id"] == "chn_c18"
    assert len(body["attempts"]) == 1
    assert body["attempts"][0]["status"] == "PASSED"
    assert body["attempts"][0]["events"][0]["result"] == "PASSED"
    assert body["attempts"][0]["events"][0]["provenance"] == "merchant_reported"


def test_the_timeline_on_a_non_challenged_chain_is_an_empty_list_not_a_409():
    _seed("chn_c19", decision=Decision.ALLOW)
    resp = _timeline("chn_c19")
    assert resp.status_code == 200
    assert resp.json()["attempts"] == []


def test_followups_never_change_the_signed_chain_record():
    chain_id = "chn_c20"
    original = _seed(chain_id)
    attempt_id = _create(chain_id).json()["attempt_id"]
    _report(chain_id, attempt_id, "FAILED")

    reread = store.get_record(chain_id)
    assert reread.verdict_json == original.verdict_json
    assert reread.signature == original.signature
    assert reread.signed_at == original.signed_at


def test_the_public_receipt_is_unaffected_by_followups():
    chain_id = "chn_c21"
    _seed(chain_id)
    before = client.get(f"/r/{chain_id}")
    attempt_id = _create(chain_id).json()["attempt_id"]
    _report(chain_id, attempt_id, "PASSED")
    after = client.get(f"/r/{chain_id}")
    assert before.status_code == after.status_code
    assert before.text == after.text
