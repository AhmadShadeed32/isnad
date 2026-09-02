"""S12 / S13 — runtime posture: docs, blocking writes, limits, bounds, leaks."""

from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app.cache import InMemoryCache
from app.config import InsecureConfiguration, Settings, check_startup_posture, settings
from app.consent import ConsentStore
from app.db import store
from app.domain.schemas import VerificationRequest
from app.main import app, create_app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


# --- the API docs ------------------------------------------------------------


def test_the_docs_follow_demo_mode(monkeypatch):
    """/docs, /redoc and /openapi.json all answered 200 unauthenticated."""
    monkeypatch.setattr(settings, "demo_mode", False)
    closed = TestClient(create_app())

    for path in ("/docs", "/redoc", "/openapi.json"):
        assert closed.get(path).status_code == 404, path


def test_the_docs_are_available_locally(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    open_app = TestClient(create_app())

    assert open_app.get("/openapi.json").status_code == 200


# --- /health (S13) -----------------------------------------------------------


def test_health_reveals_nothing_but_liveness():
    """It told an attacker whether calls cost money and whether demo was live."""
    body = client.get("/health").json()

    assert body == {"status": "ok"}


def test_the_mode_the_console_needs_is_behind_a_key():
    assert client.get("/v1/console/mode").status_code == 401

    body = client.get("/v1/console/mode", headers=AUTH).json()
    assert set(body) == {"provider", "planner", "demo_mode"}


# --- blocking writes ---------------------------------------------------------


@pytest.mark.asyncio
async def test_the_event_loop_is_not_stalled_by_a_chain_write():
    """store.* is called from async handlers; SQLite writes block.

    Under any concurrency that froze the SSE stream feeding the console.
    """
    ticks = 0

    async def heartbeat():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.001)
            ticks += 1

    beat = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.01)
    ticks = 0

    from app.chain.models import Verdict
    from app.domain.enums import Decision

    for i in range(20):
        await store.save_async(
            Verdict(
                decision=Decision.ALLOW,
                confidence=0.1,
                hypothesis="legit",
                reason="concurrency probe",
                chain_id=f"chn_probe{i:014d}",
            ),
            subject="+99999991001",
        )
    beat.cancel()

    assert ticks > 0, "the loop never got to run during the writes"


# --- rate limiting -----------------------------------------------------------


def test_a_key_is_rate_limited(monkeypatch):
    """No add_middleware call existed anywhere in the tree."""
    from app.api import rate_limit

    monkeypatch.setattr(rate_limit.per_key, "limit", 3)
    rate_limit.per_key.reset()
    try:
        codes = [client.get("/v1/console/mode", headers=AUTH).status_code for _ in range(5)]
    finally:
        rate_limit.per_key.reset()

    assert codes[:3] == [200, 200, 200]
    assert codes[3] == 429


def test_the_limiter_returns_retry_after(monkeypatch):
    from app.api import rate_limit

    monkeypatch.setattr(rate_limit.per_key, "limit", 1)
    rate_limit.per_key.reset()
    try:
        client.get("/v1/console/mode", headers=AUTH)
        limited = client.get("/v1/console/mode", headers=AUTH)
    finally:
        rate_limit.per_key.reset()

    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) >= 1


def test_the_limiter_buckets_per_key_not_globally(monkeypatch):
    from app.api import rate_limit

    monkeypatch.setattr(settings, "merchant_api_keys", "demo-merchant-key,other-key")
    monkeypatch.setattr(rate_limit.per_key, "limit", 2)
    rate_limit.per_key.reset()
    try:
        for _ in range(2):
            client.get("/v1/console/mode", headers=AUTH)
        assert client.get("/v1/console/mode", headers=AUTH).status_code == 429
        # A different key has its own budget.
        other = {"Authorization": "Bearer other-key"}
        assert client.get("/v1/console/mode", headers=other).status_code == 200
    finally:
        rate_limit.per_key.reset()


def test_the_limiter_bucket_map_is_bounded():
    from app.api.rate_limit import SlidingWindowLimiter

    limiter = SlidingWindowLimiter(limit=100, window_seconds=60.0, max_buckets=16)
    for i in range(200):
        limiter.check(f"bucket-{i}")

    assert len(limiter._buckets) <= 16


def test_the_window_actually_slides():
    from app.api.rate_limit import SlidingWindowLimiter

    limiter = SlidingWindowLimiter(limit=1, window_seconds=0.05)
    assert limiter.check("b")[0] is True
    assert limiter.check("b")[0] is False
    time.sleep(0.06)
    assert limiter.check("b")[0] is True


# --- the unbounded in-memory stores -----------------------------------------


def test_the_idempotency_cache_is_bounded():
    """Held entries for 24h and was swept only on a get of the same key."""
    cache = InMemoryCache(max_entries=50)
    for i in range(500):
        cache.set(f"idem:key:{i}", "value", 86400)

    assert len(cache) <= 50


def test_the_consent_store_is_bounded():
    from app.consent import ConsentCapacityExceeded

    consents = ConsentStore(max_records=50, max_records_per_owner=50)
    request = VerificationRequest(phone_number="+99999991000")

    for i in range(50):
        consents.create(request, f"key-{i}", "https://example.test/cb", ttl_seconds=300)
    with pytest.raises(ConsentCapacityExceeded):
        consents.create(request, "another-key", "https://example.test/cb", ttl_seconds=300)

    assert len(consents._records) == 50
    # The state index must not outlive the records it points at.
    assert len(consents._states) == 50


# --- the API key inside a cache key -----------------------------------------


def test_the_api_key_is_not_written_into_a_cache_key():
    """Harmless in memory; under Redis it lands in KEYS, MONITOR and RDB files."""
    from app.cache import cache

    client.post(
        "/v1/verify",
        headers={**AUTH, "Idempotency-Key": "posture-check"},
        json={"phone_number": "+99999991001", "context": {"event": "signup"}},
    )

    keys = getattr(cache, "_store", {}).keys()
    assert any("posture-check" in k for k in keys)
    assert not any("demo-merchant-key" in k for k in keys)


# --- S13: the redirect URI ---------------------------------------------------


def test_startup_refuses_a_localhost_redirect_on_the_billable_path(tmp_path):
    """It would redirect a judge's browser to their own machine."""
    from app.chain.vault import VaultSigner

    key_path = tmp_path / "vault-key.pem"
    VaultSigner(key_path)

    with pytest.raises(InsecureConfiguration, match="ISNAD_NAC_REDIRECT_URI"):
        check_startup_posture(
            Settings(
                _env_file=None,
                provider="nac",
                demo_mode=False,
                merchant_api_keys="a-real-key",
                nac_api_key="test-nac-key",
                subject_pepper="a-pepper",
                vault_key_path=key_path,
            )
        )


# --- S13: the SDK URL that reaches window.open() -----------------------------


def test_a_non_https_authorization_url_is_refused():
    """nac.py's _as_url returned any string the SDK provided."""
    from app.providers.nac import NacProvider

    assert NacProvider._as_url("https://consent.example/authorize")

    for bad in ("http://consent.example/authorize", "javascript:alert(1)", "//evil.test"):
        with pytest.raises(RuntimeError, match="non-HTTPS"):
            NacProvider._as_url(bad)
