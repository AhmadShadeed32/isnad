from __future__ import annotations

import time
from threading import Lock
from typing import Protocol

from app.config import InsecureConfiguration, settings


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


class CacheUnavailable(RuntimeError):
    """The configured cache backend could not be reached or constructed."""


class RedisCache:  # pragma: no cover - exercised only with a live Redis
    """Redis-backed cache for token caching + idempotency across instances.

    Every call is bounded. Without explicit timeouts a stalled Redis blocks the
    calling thread indefinitely, and these methods are invoked from `async def`
    handlers: one hung cache call took the event loop with it, so liveness and
    every unrelated request stalled behind a cache that is meant to be an
    optimisation (R14). Redis errors surface as `CacheUnavailable` rather than
    the driver's own exception, so a caller cannot leak connection details —
    which carry the host and sometimes the credential — into a response.
    """

    def __init__(self, url: str) -> None:
        import redis  # imported lazily so redis is an optional dependency

        self._errors = (redis.RedisError, OSError)
        self._r = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=settings.redis_timeout_seconds,
            socket_timeout=settings.redis_timeout_seconds,
        )

    def get(self, key: str) -> str | None:
        try:
            return self._r.get(key)
        except self._errors as exc:
            raise CacheUnavailable("cache read failed") from exc

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            self._r.set(key, value, ex=ttl_seconds or None)
        except self._errors as exc:
            raise CacheUnavailable("cache write failed") from exc

    def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        try:
            return bool(self._r.set(key, value, ex=ttl_seconds or None, nx=True))
        except self._errors as exc:
            raise CacheUnavailable("cache write failed") from exc

    def delete_if_value(self, key: str, value: str) -> bool:
        # Redis executes a Lua script atomically, so a failed request cannot
        # erase a reservation created by a later retry after the TTL elapsed.
        try:
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
        except self._errors as exc:
            raise CacheUnavailable("cache delete failed") from exc


def get_cache() -> Cache:
    """Build the configured backend, or fail.

    Asking for Redis and silently getting a process-local dictionary used to be
    the behaviour when the URL was blank or the package was missing. The
    durability the operator configured then quietly did not exist, with no
    startup error and nothing in the response to say so — and under more than
    one replica that is a correctness change, not a performance one (R14). A
    backend that cannot be constructed is now a refusal to start.
    """
    if settings.cache_backend == "memory":
        return InMemoryCache()
    if settings.cache_backend != "redis":
        raise InsecureConfiguration(
            f"ISNAD_CACHE_BACKEND={settings.cache_backend!r} is not a supported cache backend"
        )
    if not settings.redis_url:
        raise InsecureConfiguration(
            "ISNAD_CACHE_BACKEND=redis requires ISNAD_REDIS_URL; "
            "refusing to fall back to a process-local cache"
        )
    try:  # pragma: no cover - needs the optional dependency absent
        return RedisCache(settings.redis_url)
    except ImportError as exc:
        raise InsecureConfiguration(
            "ISNAD_CACHE_BACKEND=redis requires the 'redis' package; "
            "refusing to fall back to a process-local cache"
        ) from exc


# Shared cache instance (idempotency keys, and later CIBA token caching).
cache: Cache = get_cache()
