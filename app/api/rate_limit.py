from __future__ import annotations

import time
from collections import deque

from fastapi import HTTPException, Request, status

from app.config import settings
from app.judge.access import access as judge_access
from app.ownership import owner_hash

# No rate limiting existed anywhere in the tree — no add_middleware call at all
# (S12). Every route was one loop away from unbounded work, and /v1/verify in
# particular spends real money per call on the nac path.
#
# A fixed-memory sliding window per bucket. Deliberately in-process and simple:
# the deployment is a single worker (the runbook requires it, since sessions,
# consent, the SSE bus and the vault are all in-process), so a shared store
# would add a dependency without buying correctness here.


class _Window:
    __slots__ = ("hits",)

    def __init__(self) -> None:
        self.hits: deque[float] = deque()


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float, max_buckets: int = 4096) -> None:
        self.limit = limit
        self.window = window_seconds
        self.max_buckets = max_buckets
        self._buckets: dict[str, _Window] = {}

    def check(self, bucket: str) -> tuple[bool, float]:
        """(allowed, retry_after_seconds)."""
        now = time.monotonic()
        window = self._buckets.get(bucket)
        if window is None:
            self._evict(now)
            window = self._buckets[bucket] = _Window()
        hits = window.hits
        cutoff = now - self.window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.limit:
            return False, max(0.0, hits[0] + self.window - now)
        hits.append(now)
        return True, 0.0

    def _evict(self, now: float) -> None:
        """Bound the bucket map. Drops windows that are entirely in the past."""
        if len(self._buckets) < self.max_buckets:
            return
        cutoff = now - self.window
        for key, window in list(self._buckets.items()):
            if not window.hits or window.hits[-1] <= cutoff:
                del self._buckets[key]
        while len(self._buckets) >= self.max_buckets:
            del self._buckets[next(iter(self._buckets))]

    def reset(self) -> None:
        self._buckets.clear()


# Per authenticated key: the expensive routes, which cost money on the nac path.
per_key = SlidingWindowLimiter(limit=settings.rate_limit_per_key, window_seconds=60.0)
# Per client address: everything reachable without a key.
per_ip = SlidingWindowLimiter(limit=settings.rate_limit_per_ip, window_seconds=60.0)
# Tier 1 screening: high volume by design, and free to serve.
per_screen = SlidingWindowLimiter(limit=settings.rate_limit_per_key_screen, window_seconds=60.0)


def _client_ip(request: Request) -> str:
    client = request.client
    return client.host if client else "unknown"


def _reject(retry_after: float) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={"code": "rate_limited", "message": "Too many requests"},
        headers={"Retry-After": str(max(1, int(retry_after) + 1))},
    )


async def limit_per_key(request: Request) -> None:
    """Dependency for authenticated, billable routes.

    Buckets on a hash of the key, never the key itself — the same reasoning as
    the idempotency cache key.
    """
    if not settings.rate_limit_enabled:
        return
    authorization = request.headers.get("authorization", "")
    # A judge carries a scoped session instead of a merchant key, and two
    # judges at one venue share an address. Bucketing them by IP would make one
    # judge's clicking throttle the other's demonstration, so the session — the
    # thing that already separates their evidence, quota and receipts —
    # separates their rate limit too.
    judge_session = request.headers.get("x-judge-session", "").strip()
    if judge_session and judge_access.get(judge_session) is not None:
        bucket = f"judge:{owner_hash(judge_session)}"
    elif authorization.startswith("Bearer "):
        bucket = f"key:{owner_hash(authorization[7:].strip())}"
    else:
        bucket = f"ip:{_client_ip(request)}"
    allowed, retry_after = per_key.check(bucket)
    if not allowed:
        raise _reject(retry_after)


async def limit_per_ip(request: Request) -> None:
    """Dependency for routes reachable without a key."""
    if not settings.rate_limit_enabled:
        return
    allowed, retry_after = per_ip.check(f"ip:{_client_ip(request)}")
    if not allowed:
        raise _reject(retry_after)


async def limit_screen(request: Request) -> None:
    """Dependency for Tier 1 screening.

    Same bucketing as limit_per_key, a different ceiling. One inbound call is
    one screen, so a phone-facing endpoint sees traffic a merchant API never
    does — and unlike /v1/verify it costs nothing per call to serve.
    """
    if not settings.rate_limit_enabled:
        return
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        allowed, retry_after = per_screen.check(f"key:{owner_hash(authorization[7:].strip())}")
    else:
        # The raised ceiling is for identified callers. Without a key this fell
        # into the 600/min screen bucket bucketed by IP — a higher allowance for
        # an anonymous caller than any authenticated route grants a paying one.
        allowed, retry_after = per_ip.check(f"ip:{_client_ip(request)}")
    if not allowed:
        raise _reject(retry_after)
