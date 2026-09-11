"""S2 — the SSE stream must be authenticated and must not cross tenants."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.events import current_owner, emit, subscribe, subscriber_count
from app.main import app
from app.ownership import owner_hash

client = TestClient(app)


def test_anonymous_stream_is_rejected():
    """The finding, verbatim: `curl -N /v1/console/stream` harvested everything."""
    with client.stream("GET", "/v1/console/stream") as response:
        assert response.status_code == 401


def test_stream_rejects_an_unrecognized_token():
    with client.stream("GET", "/v1/console/stream?stream_token=not-a-key") as response:
        assert response.status_code == 401


def test_stream_accepts_a_stream_only_token_and_sends_a_keepalive(monkeypatch):
    """EventSource gets a short-lived stream credential, never an API key.

    Also covers the keepalive (S12): an idle stream must write something, or a
    proxy drops the judges' console mid-presentation and nobody finds out until
    the next event fails to arrive.
    """
    from app.api import routes_console, stream_token

    monkeypatch.setattr(routes_console, "SSE_KEEPALIVE_SECONDS", 0.05)
    credential = stream_token.mint(owner_hash("demo-merchant-key"))
    with client.stream("GET", f"/v1/console/stream?stream_token={credential}") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert next(response.iter_lines()) == ": keepalive"


def test_a_stream_token_cannot_authorize_a_normal_api_call():
    from app.api import stream_token

    credential = stream_token.mint(owner_hash("demo-merchant-key"))
    response = client.get("/v1/console/mode", headers={"Authorization": f"Bearer {credential}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_two_keys_running_concurrently_see_only_their_own_events():
    key_a, key_b = "key-alpha", "key-beta"

    async def collect(owner: str, into: list) -> None:
        async for event in subscribe(owner):
            into.append(event)

    seen_a: list = []
    seen_b: list = []
    task_a = asyncio.create_task(collect(owner_hash(key_a), seen_a))
    task_b = asyncio.create_task(collect(owner_hash(key_b), seen_b))
    await asyncio.sleep(0)

    current_owner.set(owner_hash(key_a))
    await emit({"type": "verdict", "chain_id": "chn_belongs_to_a"})
    current_owner.set(owner_hash(key_b))
    await emit({"type": "verdict", "chain_id": "chn_belongs_to_b"})
    await asyncio.sleep(0.01)

    task_a.cancel()
    task_b.cancel()

    assert [e["chain_id"] for e in seen_a] == ["chn_belongs_to_a"]
    assert [e["chain_id"] for e in seen_b] == ["chn_belongs_to_b"]


@pytest.mark.asyncio
async def test_a_subscriber_never_sees_an_event_emitted_for_nobody():
    """A background emit with no owner must not fan out to a real tenant."""
    seen: list = []

    async def collect() -> None:
        async for event in subscribe(owner_hash("key-alpha")):
            seen.append(event)

    task = asyncio.create_task(collect())
    await asyncio.sleep(0)
    current_owner.set(None)
    await emit({"type": "verdict", "chain_id": "chn_unowned"})
    await asyncio.sleep(0.01)
    task.cancel()

    assert seen == []


@pytest.mark.asyncio
async def test_an_investigation_reaches_only_the_caller_that_started_it():
    """End to end through the HTTP surface, not just the bus."""
    seen_eavesdropper: list = []

    async def eavesdrop() -> None:
        async for event in subscribe(owner_hash("some-other-tenant")):
            seen_eavesdropper.append(event)

    task = asyncio.create_task(eavesdrop())
    await asyncio.sleep(0)

    response = client.post(
        "/v1/verify",
        headers={"Authorization": "Bearer demo-merchant-key"},
        json={"phone_number": "+99999991001", "context": {"event": "signup"}},
    )
    assert response.status_code == 200
    await asyncio.sleep(0.01)
    task.cancel()

    assert seen_eavesdropper == []


@pytest.mark.asyncio
async def test_subscribers_are_bounded():
    """A disconnect that is never noticed must not pin memory forever (S12)."""
    from app import events

    before = subscriber_count()
    tasks = []

    async def hold() -> None:
        async for _ in subscribe("owner"):
            pass

    for _ in range(events.MAX_SUBSCRIBERS + 10):
        tasks.append(asyncio.create_task(hold()))
    await asyncio.sleep(0.02)
    assert subscriber_count() <= events.MAX_SUBSCRIBERS

    for task in tasks:
        task.cancel()
    await asyncio.sleep(0.01)
    assert subscriber_count() <= before + events.MAX_SUBSCRIBERS
