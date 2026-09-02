from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from contextvars import ContextVar

# Minimal in-process event bus for the live agent console.
# In production this is Redis pub/sub -> WebSocket/SSE; the interface is the same.
#
# Events are fanned out per owner, not process-wide (S2). The bus used to hold a
# single set of subscribers that every emit() wrote to, so anyone attached to the
# stream saw every tenant's hypotheses, evidence signals, p_fraud trajectory and
# chain_ids — the client-side run_id filter in the console is cosmetic and does
# nothing to stop that.

# Who the work currently in flight belongs to. Set once, at the authentication
# boundary; a ContextVar rather than a parameter because it then propagates
# through the whole investigation — including into the session monitor task,
# which copies the context at asyncio.create_task() — without every emit() call
# site in the investigator and the session manager having to carry an owner it
# has no other use for.
current_owner: ContextVar[str | None] = ContextVar("current_owner", default=None)

# queue -> the owner allowed to receive on it
_subscribers: dict[asyncio.Queue, str | None] = {}

# Keeps a disconnect that was never noticed from pinning memory forever.
MAX_SUBSCRIBERS = 64


def mask_phone(phone: str) -> str:
    """Keep console events useful without broadcasting a full phone number."""
    if len(phone) <= 5:
        return "*" * len(phone)
    return f"{phone[:3]}…{phone[-2:]}"


def _redact(event: dict) -> dict:
    redacted = dict(event)
    for key in ("phone_number", "caller_number", "customer_number"):
        value = redacted.get(key)
        if isinstance(value, str):
            redacted[key] = mask_phone(value)
    return redacted


async def emit(event: dict) -> None:
    """Deliver an event to the subscribers belonging to the current owner."""
    event = _redact(event)
    owner = current_owner.get()
    for q, subscriber_owner in list(_subscribers.items()):
        if subscriber_owner != owner:
            continue
        with suppress(asyncio.QueueFull):
            q.put_nowait(event)


async def subscribe(owner: str | None = None) -> AsyncIterator[dict]:
    """Receive the events emitted for `owner`, and only those."""
    q: asyncio.Queue = asyncio.Queue(maxsize=256)
    if len(_subscribers) >= MAX_SUBSCRIBERS:
        # Drop the oldest attachment rather than accept unbounded growth.
        _subscribers.pop(next(iter(_subscribers)), None)
    _subscribers[q] = owner
    try:
        while True:
            yield await q.get()
    finally:
        _subscribers.pop(q, None)


def subscriber_count() -> int:
    return len(_subscribers)
