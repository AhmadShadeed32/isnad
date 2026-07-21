from __future__ import annotations

import time
from typing import Optional, Protocol

from app.config import settings


class Cache(Protocol):
    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...


class InMemoryCache:
    """Process-local cache with TTL. Default backend; fine for a single instance.
    For multi-instance deployments, use Redis (below)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> Optional[str]:
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at and time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds else 0.0
        self._store[key] = (value, expires_at)


class RedisCache:  # pragma: no cover - exercised only with a live Redis
    """Redis-backed cache for token caching + idempotency across instances."""

    def __init__(self, url: str) -> None:
        import redis  # imported lazily so redis is an optional dependency

        self._r = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> Optional[str]:
        return self._r.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._r.set(key, value, ex=ttl_seconds or None)


def get_cache() -> Cache:
    if settings.cache_backend == "redis" and settings.redis_url:
        try:  # pragma: no cover
            return RedisCache(settings.redis_url)
        except ImportError:
            pass
    return InMemoryCache()


# Shared cache instance (idempotency keys, and later CIBA token caching).
cache: Cache = get_cache()
