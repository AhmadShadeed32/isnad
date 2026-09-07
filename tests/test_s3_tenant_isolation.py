"""S3 — one key must not be able to read another key's chain or session."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from tests.ui_source import demo_token_from

client = TestClient(app)

# Two distinct merchants, both configured.
A = {"Authorization": "Bearer key-tenant-a"}
B = {"Authorization": "Bearer key-tenant-b"}

SIGNUP = {"phone_number": "+99999991001", "context": {"event": "signup"}}


def setup_module() -> None:
    settings.merchant_api_keys = "demo-merchant-key,key-tenant-a,key-tenant-b"


def teardown_module() -> None:
    settings.merchant_api_keys = "demo-merchant-key"


def _chain_id_for(headers: dict) -> str:
    response = client.post("/v1/verify", headers=headers, json=SIGNUP)
    assert response.status_code == 200
    return response.json()["chain_id"]


def test_key_b_cannot_read_key_as_chain():
    """The finding, verbatim: store.get() was called with no ownership check."""
    chain_id = _chain_id_for(A)

    assert client.get(f"/v1/chains/{chain_id}", headers=A).status_code == 200
    assert client.get(f"/v1/chains/{chain_id}", headers=B).status_code == 404


def test_key_b_cannot_verify_the_signature_on_key_as_chain():
    """The vault route reads the same row and leaked the same way."""
    chain_id = _chain_id_for(A)

    assert client.get(f"/v1/chains/{chain_id}/verification", headers=A).status_code == 200
    assert client.get(f"/v1/chains/{chain_id}/verification", headers=B).status_code == 404


def test_a_foreign_chain_is_indistinguishable_from_a_missing_one():
    """404, not 403: an id must not be probeable for existence."""
    chain_id = _chain_id_for(A)

    foreign = client.get(f"/v1/chains/{chain_id}", headers=B)
    missing = client.get("/v1/chains/chn_0000000000000000dead", headers=B)
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json()["detail"]["code"] == missing.json()["detail"]["code"]


def test_key_b_cannot_read_or_end_key_as_session():
    created = client.post(
        "/v1/sessions", headers=A, json={"phone_number": "+962790000001", "ttl_seconds": 30}
    )
    assert created.status_code == 200
    session_id = created.json()["session_id"]
    try:
        assert client.get(f"/v1/sessions/{session_id}", headers=A).status_code == 200
        assert client.get(f"/v1/sessions/{session_id}", headers=B).status_code == 404
        # A borrowed key must not be able to revoke someone else's live trust.
        assert client.delete(f"/v1/sessions/{session_id}", headers=B).status_code == 404
        assert client.get(f"/v1/sessions/{session_id}", headers=A).json()["status"] == "ACTIVE"
    finally:
        client.delete(f"/v1/sessions/{session_id}", headers=A)


def test_a_session_response_never_carries_a_full_phone_number():
    created = client.post(
        "/v1/sessions", headers=A, json={"phone_number": "+962790000001", "ttl_seconds": 30}
    )
    session_id = created.json()["session_id"]
    try:
        assert "+962790000001" not in created.text
        assert created.json()["phone_number"] == "+96…01"

        swap = client.post(f"/v1/sessions/{session_id}/simulate-swap", headers=A)
        assert swap.status_code == 200
        assert "+962790000001" not in swap.text
    finally:
        client.delete(f"/v1/sessions/{session_id}", headers=A)


def test_a_chain_is_readable_by_the_key_that_created_it():
    """The isolation must not have broken the ordinary path."""
    chain_id = _chain_id_for(B)
    response = client.get(f"/v1/chains/{chain_id}", headers=B)
    assert response.status_code == 200
    assert response.json()["chain_id"] == chain_id


def test_a_console_reload_does_not_orphan_the_chains_it_created():
    """A token is minted per render; the tenant it maps to must be stable.

    Owning by token would mean reloading the console 404s the "verify this
    chain" button on stage, because every chain was created under the previous
    render's token.
    """
    before = _console_token()
    chain_id = _chain_id_for({"Authorization": f"Bearer {before}"})
    after = _console_token()
    assert before != after

    response = client.get(f"/v1/chains/{chain_id}", headers={"Authorization": f"Bearer {after}"})
    assert response.status_code == 200


def test_a_console_token_cannot_read_a_merchants_chain():
    chain_id = _chain_id_for(A)
    token = _console_token()
    response = client.get(f"/v1/chains/{chain_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def _console_token() -> str:
    return demo_token_from(client.get("/console").text)
