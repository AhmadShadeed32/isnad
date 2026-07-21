from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress

# Minimal in-process event bus for the live agent console.
# In production this is Redis pub/sub -> WebSocket/SSE; the interface is the same.

_subscribers: set[asyncio.Queue] = set()


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
    event = _redact(event)
    for q in list(_subscribers):
        with suppress(asyncio.QueueFull):
            q.put_nowait(event)


async def subscribe() -> AsyncIterator[dict]:
    q: asyncio.Queue = asyncio.Queue(maxsize=256)
    _subscribers.add(q)
    try:
        while True:
            yield await q.get()
    finally:
        _subscribers.discard(q)
