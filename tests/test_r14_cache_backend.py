"""R14 — a cache backend that cannot be built must refuse, not pretend.

Asking for Redis and silently getting a process-local dictionary changed the
durability the operator configured, with no startup error and nothing in any
response to say so. Under more than one replica that is a correctness change:
two instances each believe they hold the idempotency reservations, and neither
sees the other's.
"""

from __future__ import annotations

import pytest

from app import cache as cache_module
from app.cache import CacheUnavailable, InMemoryCache, get_cache
from app.config import InsecureConfiguration


def test_memory_is_still_the_default(monkeypatch):
    monkeypatch.setattr(cache_module.settings, "cache_backend", "memory")
    assert isinstance(get_cache(), InMemoryCache)


def test_redis_without_a_url_refuses_instead_of_falling_back(monkeypatch):
    monkeypatch.setattr(cache_module.settings, "cache_backend", "redis")
    monkeypatch.setattr(cache_module.settings, "redis_url", None)

    with pytest.raises(InsecureConfiguration, match="ISNAD_REDIS_URL"):
        get_cache()


def test_a_missing_redis_package_refuses_instead_of_falling_back(monkeypatch):
    monkeypatch.setattr(cache_module.settings, "cache_backend", "redis")
    monkeypatch.setattr(cache_module.settings, "redis_url", "redis://localhost:6379/0")

    def no_redis(url):
        raise ImportError("No module named 'redis'")

    monkeypatch.setattr(cache_module, "RedisCache", no_redis)
    with pytest.raises(InsecureConfiguration, match="redis"):
        get_cache()


def test_an_unknown_backend_is_refused(monkeypatch):
    monkeypatch.setattr(cache_module.settings, "cache_backend", "memcached")

    with pytest.raises(InsecureConfiguration, match="memcached"):
        get_cache()


def test_an_unavailable_cache_does_not_fail_the_request(monkeypatch):
    """Bounded degradation: the durable record answers instead (R13/R14)."""
    from fastapi.testclient import TestClient

    from app.cache import cache
    from app.main import app

    def explode(*args, **kwargs):
        raise CacheUnavailable("redis is down")

    monkeypatch.setattr(cache, "get", explode)
    monkeypatch.setattr(cache, "set", explode)
    client = TestClient(app)

    response = client.post(
        "/v1/verify",
        headers={"Authorization": "Bearer demo-merchant-key", "Idempotency-Key": "r14-down"},
        json={"phone_number": "+99999991001", "context": {"event": "signup"}},
    )

    assert response.status_code == 200
    # And liveness is unaffected by the cache being unreachable.
    assert client.get("/readyz").status_code == 200


def test_redis_calls_are_bounded_by_an_explicit_timeout(monkeypatch):
    """An unbounded socket call from an async handler blocks the event loop.

    `redis` is an optional dependency and is not installed here, so a stub
    stands in for it. What is under test is the arguments this code passes,
    which is exactly what the stub can observe.
    """
    import sys
    import types

    captured: dict = {}

    class FakeRedis:
        @staticmethod
        def from_url(url, **kwargs):
            captured.update(kwargs)
            return object()

    stub = types.ModuleType("redis")
    stub.Redis = FakeRedis
    stub.RedisError = type("RedisError", (Exception,), {})
    monkeypatch.setitem(sys.modules, "redis", stub)

    cache_module.RedisCache("redis://localhost:6379/0")

    assert captured["socket_timeout"] == cache_module.settings.redis_timeout_seconds
    assert captured["socket_connect_timeout"] == cache_module.settings.redis_timeout_seconds
