"""A ceiling on how much of the *deployment's own* model quota strangers may spend.

A public demo that carries its own Gemini key is a stranger's budget to burn:
one header selects the model planner, and nothing about the request costs the
caller anything. The per-investigation cap does not help, because there is no
limit on investigations.

So this counts model calls made on the deployment's key inside a rolling
window, and once the ceiling is reached `effective_gemini_key()` stops handing
that key out. The run then falls back to greedy exactly as it does when no key
is configured at all — a path this project already takes seriously, because the
verdict records which planner actually chose. The demo degrades; it does not
lie, and it does not bill.

A key supplied *on the request* is deliberately not counted. That is the
reviewer's own quota, spent on their own say-so, and rationing it would be
rude and pointless.

Process-local, like every other counter here. One worker, one replica — the
same constraint the rest of the service already documents.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from app.config import settings

_lock = threading.Lock()
_calls: deque[float] = deque()

WINDOW_SECONDS = 3600.0


def _prune(now: float) -> None:
    cutoff = now - WINDOW_SECONDS
    while _calls and _calls[0] < cutoff:
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
    now = time.monotonic()
    with _lock:
        _prune(now)
        return len(_calls) >= ceiling


def note_model_call() -> None:
    """Record one model call charged to the deployment's key."""
    if settings.llm_max_calls_per_hour <= 0:
        return
    now = time.monotonic()
    with _lock:
        _prune(now)
        _calls.append(now)


def calls_in_window() -> int:
    now = time.monotonic()
    with _lock:
        _prune(now)
        return len(_calls)


def reset() -> None:
    """For tests, which must not inherit another test's spending."""
    with _lock:
        _calls.clear()
