"""Regression tests for audit fixes: engine caching + auth hardening."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.policy.engine import get_engine

client = TestClient(app)


def test_engine_is_cached():
    a = get_engine(str(settings.policy_path))
    b = get_engine(str(settings.policy_path))
    assert a is b  # loaded once, reused


def test_invalid_api_key_is_rejected():
    r = client.post(
        "/v1/verify",
        headers={"Authorization": "Bearer not-a-real-key"},
        json={"phone_number": "+962790000001"},
    )
    assert r.status_code == 403


def test_missing_bearer_is_rejected():
    r = client.post(
        "/v1/verify",
        headers={"Authorization": "demo-merchant-key"},  # no "Bearer " prefix
        json={"phone_number": "+962790000001"},
    )
    assert r.status_code == 401
