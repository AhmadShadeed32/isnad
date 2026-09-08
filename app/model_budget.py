"""A ceiling on how much of the *deployment's own* model quota strangers may spend.

A public demo that carries its own Gemini key is a stranger's budget to burn:
one header selects the model planner, and nothing about the request costs the
caller anything. The per-investigation cap does not help, because there is no
limit on investigations.

Every outgoing Gemini request must reserve a slot atomically, immediately
before transport. Checking when a client is created is insufficient: clients
are reused, and concurrent requests can pass the same availability check.
Failed attempts keep their reservation because the provider may already have
received and charged them.

A different key supplied on the request spends the reviewer's own quota and is
not counted. Supplying the deployment's key still spends deployment quota.

Process-local, like every other counter here. One worker, one replica — the
same constraint the rest of the service already documents.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from app.config import settings
from app.runtime_keys import uses_server_key

_lock = threading.Lock()
_calls: deque[float] = deque()

WINDOW_SECONDS = 3600.0


def _prune(now: float) -> None:
    cutoff = now - WINDOW_SECONDS
    while _calls and _calls[0] <= cutoff:
        _calls.popleft()


def budget_exhausted() -> bool:
    """Whether the deployment's own key has hit its ceiling for this window.

    A ceiling of 0 means unlimited, which is the default: a developer running
    locally on their own key should not meet a rationing scheme, and neither
    should a deployment whose key belongs to the person operating it.
    """
    ceiling = settings.llm_max_calls_per_hour
    if ceiling <= 0:
        return False
    with _lock:
        _prune(time.monotonic())
        return len(_calls) >= ceiling


def reserve_model_call(api_key: str) -> bool:
    """Admit one outgoing request, counting the actual credential it will use.

    Return False without changing the count when the ceiling is reached. The
    check and reservation share one lock, including the timestamp read, so
    concurrent workers cannot overspend or put the rolling window out of order.
    """
    ceiling = settings.llm_max_calls_per_hour
    if ceiling <= 0 or not uses_server_key(api_key):
        return True
    with _lock:
        now = time.monotonic()
        _prune(now)
        if len(_calls) >= ceiling:
            return False
        _calls.append(now)
        return True


def calls_in_window() -> int:
    with _lock:
        _prune(time.monotonic())
        return len(_calls)


def reset() -> None:
    """For tests, which must not inherit another test's spending."""
    with _lock:
        _calls.clear()
