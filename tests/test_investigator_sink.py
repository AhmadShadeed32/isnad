"""I1 shared contract, step 6: Investigator accepts an injectable planner and
event_sink without changing its default (emit-based) behavior for existing
callers."""

from __future__ import annotations

import pytest

from app.agent.investigator import build_investigator
from app.domain.schemas import RequestContext, VerificationRequest
from app.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_a_custom_event_sink_receives_every_emission_instead_of_the_bus():
    recorded: list[dict] = []

    async def sink(event: dict) -> None:
        recorded.append(event)

    investigator = build_investigator(MockProvider(), event_sink=sink)
    req = VerificationRequest(
        phone_number="+962790000001", context=RequestContext(event="signup", account_age_days=0)
    )
    await investigator.investigate(req)

    assert recorded, "the injected sink must receive the same emissions emit() would have"
    assert any(e.get("type") == "start" for e in recorded)


@pytest.mark.asyncio
async def test_the_default_sink_is_still_the_shared_event_bus():
    """Unchanged behavior for every existing caller that does not inject one."""
    import asyncio

    from app.events import current_owner, subscribe

    token = current_owner.set("test-owner-sink")
    subscriber = subscribe("test-owner-sink")
    try:
        # Prime the subscription (registers with the bus) before emitting, or
        # the generator's own registration races the investigation's emits.
        recv_task = asyncio.ensure_future(subscriber.__anext__())
        await asyncio.sleep(0)
        investigator = build_investigator(MockProvider())
        req = VerificationRequest(
            phone_number="+962790000002", context=RequestContext(event="signup", account_age_days=0)
        )
        await investigator.investigate(req)
        first_event = await asyncio.wait_for(recv_task, timeout=1.0)
    finally:
        current_owner.reset(token)
        await subscriber.aclose()

    assert first_event, "with no injected sink, emissions must still reach the shared bus"
