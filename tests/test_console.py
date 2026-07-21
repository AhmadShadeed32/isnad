"""Console page, demo-trigger endpoint, and the live event bus."""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.agent.investigator import build_investigator
from app.domain.schemas import Money, RequestContext, VerificationRequest
from app.events import subscribe
from app.main import app
from app.providers.mock import MockProvider

client = TestClient(app)


def test_console_page_serves():
    r = client.get("/console")
    assert r.status_code == 200
    assert "Isnad" in r.text
    assert "/v1/console/stream" in r.text  # wired to the live stream


def test_console_run_act1_allows():
    r = client.post("/v1/console/run/act1")
    assert r.status_code == 200
    assert r.json()["decision"] == "ALLOW"


def test_console_run_unknown_act_404():
    r = client.post("/v1/console/run/nope")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_event_bus_streams_start_and_verdict():
    """A run must emit a 'start' first and a 'verdict' last to any subscriber."""
    events: list[dict] = []

    async def collect():
        async for ev in subscribe():
            events.append(ev)
            if ev["type"] == "verdict":
                return

    task = asyncio.create_task(collect())
    await asyncio.sleep(0.05)  # let the subscriber register

    req = VerificationRequest(
        phone_number="+962790000002",
        context=RequestContext(event="checkout", payment_method="cod",
                               account_age_days=0, amount=Money(value=4200)),
    )
    await build_investigator(MockProvider()).investigate(req, run_id="console-test")
    await asyncio.wait_for(task, timeout=2.0)

    assert events[0]["type"] == "start"
    assert events[-1]["type"] == "verdict"
    assert any(e["type"] == "evidence" for e in events)
    assert all(e["run_id"] == "console-test" for e in events)
