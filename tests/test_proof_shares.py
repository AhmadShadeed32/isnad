"""I13 — expiring reviewer links with explicit disclosure scope.

A proof share is a separately issued attestation, never a redacted copy of
the original signature and never a second path to the original chain URL.
Revoking a share disables future access through *that link*; it does not
revoke the already-public original receipt or erase anything downloaded.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.chain.models import Verdict
from app.chain.vault import vault
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
        hypothesis="legit",
        reason="",
        chain_id=chain_id,
    )
    return store.save(verdict)


def _create(chain_id: str, headers=None, **body):
    return client.post(
        f"/v1/chains/{chain_id}/proof-shares",
        json={"purpose": "reviewer link", **body},
        headers=headers or _fresh_headers(AUTH),
    )


# --- creation --------------------------------------------------------------


def test_a_share_can_be_created_on_an_owned_chain():
    _seed("chn_ps1")
    resp = _create("chn_ps1")
    assert resp.status_code == 201
    body = resp.json()
    assert body["token"]
    assert body["chain_id"] == "chn_ps1"


def test_creating_a_share_on_a_missing_chain_is_404():
    resp = _create("chn_does_not_exist")
    assert resp.status_code == 404


def test_a_foreign_key_cannot_create_a_share():
    _seed("chn_ps2")
    resp = _create("chn_ps2", headers=_fresh_headers(OTHER_AUTH))
    assert resp.status_code == 404


def test_creating_a_share_requires_authentication():
    _seed("chn_ps3")
    resp = client.post(
        "/v1/chains/chn_ps3/proof-shares", json={"purpose": "x"}, headers={"Idempotency-Key": "k"}
    )
    assert resp.status_code == 401


def test_creating_a_share_requires_an_idempotency_key():
    _seed("chn_ps4")
    resp = client.post(
        "/v1/chains/chn_ps4/proof-shares",
        json={"purpose": "x"},
        headers={"Authorization": AUTH["Authorization"]},
    )
    assert resp.status_code == 422


def test_a_free_text_field_is_rejected():
    _seed("chn_ps5")
    resp = _create("chn_ps5", notes="please review urgently")
    assert resp.status_code == 422


def test_a_ttl_beyond_the_maximum_is_rejected():
    _seed("chn_ps6")
    resp = _create("chn_ps6", ttl_seconds=99_999_999)
    assert resp.status_code == 422


# --- idempotency (durable, encrypted-at-rest token) --------------------------


def test_retrying_the_same_key_and_body_replays_the_same_token():
    _seed("chn_ps7")
    key = _fresh_headers(AUTH)
    first = _create("chn_ps7", headers=key)
    second = _create("chn_ps7", headers=key)
    assert first.json()["token"] == second.json()["token"]
    assert first.json()["share_id"] == second.json()["share_id"]


def test_reusing_a_key_against_a_different_chain_is_a_conflict():
    _seed("chn_ps8a")
    _seed("chn_ps8b")
    key = _fresh_headers(AUTH)
    first = _create("chn_ps8a", headers=key)
    assert first.status_code == 201
    second = _create("chn_ps8b", headers=key)
    assert second.status_code == 409


def test_the_stored_idempotency_response_never_contains_the_plaintext_token():
    """The token must be recoverable for a replay, but never sit in the
    database in the clear (the spec's own encrypted-response-retention rule)."""
    from app.db.database import SessionLocal
    from app.db.models import IdempotencyRecordRow
    from app.ownership import owner_hash

    _seed("chn_ps9")
    key = _fresh_headers(AUTH)
    created = _create("chn_ps9", headers=key)
    token = created.json()["token"]

    with SessionLocal() as session:
        row = session.get(
            IdempotencyRecordRow, (owner_hash("demo-merchant-key"), "proof_share.create", key["Idempotency-Key"])
        )
        assert row is not None
        assert token not in row.response_json


# --- public read: /p/{token} ------------------------------------------------


def test_a_valid_token_returns_a_signed_attestation():
    _seed("chn_ps10")
    created = _create("chn_ps10").json()
    resp = client.get(f"/p/{created['token']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chain_id"] == "chn_ps10"
    assert body["decision"] == "CHALLENGE"
    assert body["type"] != "Verdict"  # domain-separated, never confusable with the signed Verdict
    assert "signature" in body


def test_the_attestation_signature_verifies_against_the_issuer_key():
    _seed("chn_ps11")
    created = _create("chn_ps11").json()
    resp = client.get(f"/p/{created['token']}").json()
    payload = {k: v for k, v in resp.items() if k not in ("signature",)}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert vault.verify(canonical, resp["signature"])


def test_an_unknown_token_is_unavailable():
    resp = client.get("/p/not-a-real-token")
    assert resp.status_code == 404


def test_a_revoked_share_reads_the_same_as_a_missing_one():
    _seed("chn_ps12")
    created = _create("chn_ps12").json()
    client.delete(f"/v1/chains/chn_ps12/proof-shares/{created['share_id']}", headers=_fresh_headers(AUTH))
    resp = client.get(f"/p/{created['token']}")
    assert resp.status_code == 404


def test_an_expired_share_reads_the_same_as_a_missing_one(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "proof_share_default_ttl_seconds", 0)
    _seed("chn_ps13")
    created = _create("chn_ps13").json()
    import time

    time.sleep(0.01)
    resp = client.get(f"/p/{created['token']}")
    assert resp.status_code == 404


def test_the_public_response_has_no_store_and_no_referrer_headers():
    _seed("chn_ps14")
    created = _create("chn_ps14").json()
    resp = client.get(f"/p/{created['token']}")
    assert "no-store" in resp.headers.get("cache-control", "")
    assert resp.headers.get("referrer-policy") == "no-referrer"


# --- revocation --------------------------------------------------------------


def test_revocation_is_idempotent():
    _seed("chn_ps15")
    created = _create("chn_ps15").json()
    first = client.delete(f"/v1/chains/chn_ps15/proof-shares/{created['share_id']}", headers=_fresh_headers(AUTH))
    second = client.delete(f"/v1/chains/chn_ps15/proof-shares/{created['share_id']}", headers=_fresh_headers(AUTH))
    assert first.status_code == 204
    assert second.status_code == 204


def test_a_foreign_key_cannot_revoke_someone_elses_share():
    _seed("chn_ps16")
    created = _create("chn_ps16").json()
    resp = client.delete(
        f"/v1/chains/chn_ps16/proof-shares/{created['share_id']}", headers=_fresh_headers(OTHER_AUTH)
    )
    assert resp.status_code == 404


def test_revoking_a_share_does_not_touch_the_original_receipt():
    chain_id = "chn_ps17"
    original = _seed(chain_id)
    created = _create(chain_id).json()
    client.delete(f"/v1/chains/{chain_id}/proof-shares/{created['share_id']}", headers=_fresh_headers(AUTH))

    reread = store.get_record(chain_id)
    assert reread.verdict_json == original.verdict_json
    assert reread.signature == original.signature

    receipt = client.get(f"/r/{chain_id}")
    assert receipt.status_code == 200


# --- no leaked data ------------------------------------------------------------


def test_the_attestation_never_carries_full_chain_or_merchant_or_session_data():
    _seed("chn_ps18")
    created = _create("chn_ps18").json()
    body = client.get(f"/p/{created['token']}").json()
    serialized = json.dumps(body)
    assert "chain" not in body  # no evidence link list
    for forbidden in ("owner_hash", "session_id", "attempt_id", "outcome"):
        assert forbidden not in serialized
