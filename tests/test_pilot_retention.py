"""Idle retention and one trust-session binding per merchant order."""

import asyncio
from datetime import timedelta

import httpx
import pytest

from tests.test_review_regressions import add_flow, client_for, pilot, upstream


@pytest.mark.asyncio
async def test_idle_cleanup_and_shutdown(monkeypatch):
    now = pilot._now()
    monkeypatch.setattr(pilot, "_now", lambda: now)
    monkeypatch.setattr(pilot, "CLEANUP_INTERVAL_SECONDS", 0.001)
    monkeypatch.setattr(pilot, "flows", pilot.FlowStore(10))
    monkeypatch.setattr(pilot, "sessions", pilot.SessionStore(10))
    owner = pilot.sessions.create()
    old = add_flow(owner.session_id)
    now += timedelta(seconds=11)
    fresh = add_flow(owner.session_id, flow_id="flw_fresh", created_at=now)
    # Put the expired record back without invoking request-time cleanup.
    pilot.flows._flows[old.flow_id] = old
    async with pilot.app.router.lifespan_context(pilot.app):
        await asyncio.sleep(0.02)
        assert old.flow_id not in pilot.flows._flows
        assert fresh.flow_id in pilot.flows._flows
        assert owner.session_id not in pilot.sessions._sessions
        task = pilot.app.state.cleanup_task
    assert task.done()


@pytest.mark.parametrize("state", ["COMPLETED", "DENIED", "FAILED", "EXPIRED", "UNAVAILABLE"])
def test_terminal_reads_remove_authorization_material(monkeypatch, state):
    owner = pilot.sessions.create()
    flow = add_flow(owner.session_id, status=state)
    response = client_for(owner).get(f"/api/flows/{flow.flow_id}")
    assert response.status_code == 200
    assert response.json()["authorization_url"] == ""
    assert response.json()["qr_svg"] == ""
    if state != "COMPLETED":
        assert flow.phone_number == ""


def test_trust_session_binding_is_not_replaced(monkeypatch):
    owner = pilot.sessions.create()
    flow = add_flow(owner.session_id)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"session_id": "sess_original", "status": "ACTIVE"})

    upstream(monkeypatch, handler)
    client = client_for(owner)
    for _ in range(2):
        response = client.post(
            f"/api/flows/{flow.flow_id}/trust-session",
            headers={"X-CSRF-Token": owner.csrf_token},
            json={},
        )
        assert response.status_code == 200
        assert response.json()["session_id"] == "sess_original"
    assert len(calls) == 1
    assert flow.phone_number == ""


def test_completed_phone_expires_without_a_request(monkeypatch):
    now = pilot._now()
    monkeypatch.setattr(pilot, "_now", lambda: now)
    owner = pilot.sessions.create()
    flow = add_flow(owner.session_id)
    flow.minimize()
    assert flow.phone_number
    now += timedelta(seconds=pilot.PHONE_RETENTION_SECONDS + 1)
    pilot.flows.purge()
    assert flow.phone_number == ""
    response = client_for(owner).post(
        f"/api/flows/{flow.flow_id}/trust-session",
        headers={"X-CSRF-Token": owner.csrf_token}, json={},
    )
    assert response.status_code == 410


@pytest.mark.parametrize("store", [pilot.FlowStore, pilot.SessionStore])
@pytest.mark.parametrize("ttl", [0, -1])
def test_retention_must_be_positive(store, ttl):
    with pytest.raises(ValueError):
        store(ttl)
