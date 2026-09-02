from __future__ import annotations

import time
from threading import Lock
from typing import Protocol

from app.config import settings


class Cache(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...
    def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool: ...
    def delete_if_value(self, key: str, value: str) -> bool: ...


# The idempotency cache holds entries for 24 hours and used to be swept only on
# a `get` of the same key — so a stream of distinct keys grew it without bound
# and nothing ever reclaimed them (S12).
MAX_CACHE_ENTRIES = 10_000


class CacheCapacityExceeded(RuntimeError):
    """A new idempotency reservation cannot displace an existing one."""


class InMemoryCache:
    """Process-local cache with TTL. Default backend; fine for a single instance.
    For multi-instance deployments, use Redis (below)."""

    def __init__(self, max_entries: int = MAX_CACHE_ENTRIES) -> None:
        self._store: dict[str, tuple[str, float]] = {}
        self._max_entries = max_entries
        self._lock = Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._get_unlocked(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        with self._lock:
            self._set_unlocked(key, value, ttl_seconds)

    def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        """Atomically reserve ``key`` if no non-expired value exists.

        Idempotency uses this before it starts billable work. A separate
        get-then-set sequence permits two concurrent requests to both perform
        that work; this lock mirrors Redis' ``SET ... NX`` semantics locally.
        """
        with self._lock:
            if self._get_unlocked(key) is not None:
                return False
            self._purge_expired_unlocked()
            if len(self._store) >= self._max_entries:
                # The normal cache can evict an old value to remain bounded.
                # An idempotency reservation cannot: evicting a live pending
                # entry reopens a window for a duplicate billable request.
                raise CacheCapacityExceeded("idempotency reservation capacity is full")
            expires_at = time.monotonic() + ttl_seconds if ttl_seconds else 0.0
            self._store[key] = (value, expires_at)
            return True

    def delete_if_value(self, key: str, value: str) -> bool:
        """Release an unfinished reservation without deleting a newer one."""
        with self._lock:
            if self._get_unlocked(key) != value:
                return False
            self._store.pop(key, None)
            return True

    def _get_unlocked(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at and time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def _set_unlocked(self, key: str, value: str, ttl_seconds: int) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds else 0.0
        if key not in self._store and len(self._store) >= self._max_entries:
            self._evict()
        self._store[key] = (value, expires_at)

    def _evict(self) -> None:
        """Drop what has expired; if nothing has, drop the oldest inserted."""
        expired = self._purge_expired_unlocked()
        if not expired and self._store:
            del self._store[next(iter(self._store))]

    def _purge_expired_unlocked(self) -> list[str]:
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if exp and exp <= now]
        for key in expired:
            del self._store[key]
        return expired

    def __len__(self) -> int:
        return len(self._store)


class RedisCache:  # pragma: no cover - exercised only with a live Redis
    """Redis-backed cache for token caching + idempotency across instances."""

    def __init__(self, url: str) -> None:
        import redis  # imported lazily so redis is an optional dependency

        self._r = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> str | None:
        return self._r.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._r.set(key, value, ex=ttl_seconds or None)

    def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        return bool(self._r.set(key, value, ex=ttl_seconds or None, nx=True))

    def delete_if_value(self, key: str, value: str) -> bool:
        # Redis executes a Lua script atomically, so a failed request cannot
        # erase a reservation created by a later retry after the TTL elapsed.
        return bool(
            self._r.eval(
                """
                if redis.call('get', KEYS[1]) == ARGV[1] then
                    return redis.call('del', KEYS[1])
                end
                return 0
                """,
                1,
                key,
                value,
            )
        )


def get_cache() -> Cache:
    if settings.cache_backend == "redis" and settings.redis_url:
        try:  # pragma: no cover
            return RedisCache(settings.redis_url)
        except ImportError:
            pass
    return InMemoryCache()


# Shared cache instance (idempotency keys, and later CIBA token caching).
cache: Cache = get_cache()
