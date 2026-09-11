from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import suppress
from contextvars import ContextVar

log = logging.getLogger("isnad")

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
    """Deliver an event to the subscribers belonging to the current owner.

    Persisted before fan-out (I14) when the event carries a `run_id` — most
    emissions never do, and only a `run_id`'d run is ever replayable. A
    persistence failure is logged and swallowed rather than raised: it must
    never abort the live investigation the event belongs to, and the
    resulting gap is a fact the replay reader can detect for itself (see
    `app.db.run_events.has_gap`), not one this call pretends did not happen.

    The sequence the journal assigned rides along on the live event. Without
    it a reconnecting client has no key it can match the two deliveries on:
    I14 promises at-least-once, so the same event legitimately arrives twice
    (once live, once replayed) and the UI has to be able to tell that it is
    the same one. An event that failed to persist carries no sequence — it is
    live-only and unrecoverable, and saying so is better than numbering it as
    if it were in the journal.
    """
    event = _redact(event)
    owner = current_owner.get()
    run_id = event.get("run_id")
    if run_id:
        try:
            from app.db import run_events
            from app.ownership import ANONYMOUS

            sequence = await asyncio.to_thread(
                run_events.persist_event, owner or ANONYMOUS, run_id, event
            )
            if sequence is not None:
                event["sequence"] = sequence
        except Exception:
            log.exception("run event persistence failed for run_id=%s", run_id)
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
