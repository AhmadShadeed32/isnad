"""The judge page is a safe presentation client over existing demo APIs."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.api import routes_judge
from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_limiters():
    """The public page is address-limited; do not leak this traffic to tests
    that intentionally exercise the limiter at an exact boundary."""
    from app.api import rate_limit

    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()
    rate_limit.per_screen.reset()
    yield
    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()
    rate_limit.per_screen.reset()


def _page_body() -> str:
    return asyncio.run(routes_judge.judge_page()).body.decode("utf-8")


def test_judge_page_is_a_checkout_to_signed_receipt_story():
    page = _page_body()

    assert "Investigate the SIM change" in page
    assert "Try a clean checkout" in page
    assert "Evidence decision trace" in page
    assert "Open signed receipt" in page
    assert "Ed25519" in page
    assert "Continue trust after checkout" in page
    assert "Simulate SIM swap" in page


def test_judge_route_is_mounted_with_the_console_page_hardening():
    response = client.get("/judge")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "content-security-policy" in response.headers


def test_judge_page_uses_the_existing_authenticated_console_fixture_only():
    """Judge Mode is not a second route for arbitrary provider calls.

    It must use the fixed Act VI replacement and Act III clean fixtures.  The route has no user-controlled request fields.
    """
    page = _page_body()

    assert "/v1/console/run/act3" in page
    assert "/v1/console/run/act6" in page
    assert "addEventListener('click', () => runCheckout('replacement'))" in page
    assert "/v1/console/stream?stream_token=" in page
    assert "/v1/console/stream-token" in page
    assert "/v1/chains/" in page  # existing vault verification endpoint
    assert "'/v1/sessions'" in page
    assert "/simulate-swap" in page
    assert "phone_number:'+99999991002'" in page
    assert "/v1/verify" not in page
    assert "innerHTML" not in page


def test_judge_page_mints_a_short_lived_token_only_in_demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    demo_page = _page_body()
    assert "__ISNAD_JUDGE_TOKEN__" not in demo_page
    assert "const DEMO_TOKEN = 'demo_" in demo_page

    monkeypatch.setattr(settings, "demo_mode", False)
    production_page = _page_body()
    assert "const DEMO_TOKEN = '';" in production_page
