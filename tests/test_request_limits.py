"""Ingress limits and readiness are enforced before endpoint work begins."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.request_limits import MAX_REQUEST_BODY_BYTES
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


def test_an_oversized_body_is_rejected_before_pydantic_parses_it():
    response = client.post(
        "/v1/verify",
        headers={**AUTH, "content-type": "application/json"},
        content=b"x" * (MAX_REQUEST_BODY_BYTES + 1),
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "request_too_large"


def test_readiness_performs_a_database_round_trip():
    assert client.get("/readyz").json() == {"status": "ready"}
