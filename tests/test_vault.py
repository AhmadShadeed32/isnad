"""Evidence vault — signed, tamper-evident chains."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.db.models import ChainRow
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


def _make_chain() -> str:
    r = client.post(
        "/v1/verify",
        headers=AUTH,
        json={"phone_number": "+962790000002",
              "context": {"event": "checkout", "payment_method": "cod",
                          "account_age_days": 0, "amount": {"value": 4200}}},
    )
    assert r.status_code == 200
    return r.json()["chain_id"]


def test_public_key_is_ed25519_hex():
    r = client.get("/v1/vault/public-key")
    assert r.status_code == 200
    assert r.json()["algorithm"] == "Ed25519"
    assert len(r.json()["public_key"]) == 64  # 32-byte raw key, hex


def test_fresh_chain_verifies():
    cid = _make_chain()
    r = client.get(f"/v1/chains/{cid}/verification", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["algorithm"] == "Ed25519"
    assert body["signature"]


def test_tampered_chain_fails_verification():
    cid = _make_chain()
    # Tamper directly in the database: flip the decision in the stored JSON.
    with SessionLocal() as s:
        row = s.get(ChainRow, cid)
        row.verdict_json = row.verdict_json.replace("DECLINE", "ALLOW")
        s.add(row)
        s.commit()
    r = client.get(f"/v1/chains/{cid}/verification", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["valid"] is False


def test_chain_persists_and_round_trips():
    cid = _make_chain()
    r = client.get(f"/v1/chains/{cid}", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["decision"] == "DECLINE"
    assert r.json()["chain"]
