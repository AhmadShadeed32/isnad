"""I14's HTTP surface: GET /v1/console/runs/{run_id}/events.

Authorized the same way every other console route is -- through
require_api_key -- never derived from the run_id alone, which a client
could simply guess or copy from another tenant's own console session.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.events import current_owner, emit
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}
OTHER_AUTH = {"Authorization": "Bearer other-merchant-key"}


@pytest.fixture(autouse=True)
def _extra_merchant_key(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "merchant_api_keys", "demo-merchant-key,other-merchant-key")


@pytest.fixture(autouse=True)
def _reset_limiters():
    from app.api import rate_limit

    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()
    yield
    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()


async def _seed_run(owner: str, run_id: str, n: int = 3) -> None:
    from app.ownership import owner_hash

    token = current_owner.set(owner_hash(owner))
    try:
        for i in range(n):
            await emit({"type": "evidence", "run_id": run_id, "step": i})
    finally:
        current_owner.reset(token)


@pytest.mark.asyncio
async def test_the_owner_can_replay_their_own_run():
    await _seed_run("demo-merchant-key", "run_http_1")
    resp = client.get("/v1/console/runs/run_http_1/events", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["events"]) == 3
    assert body["gap"] is False


@pytest.mark.asyncio
async def test_a_foreign_key_sees_nothing_for_someone_elses_run():
    await _seed_run("demo-merchant-key", "run_http_2")
    resp = client.get("/v1/console/runs/run_http_2/events", headers=OTHER_AUTH)
    assert resp.status_code == 200
    assert resp.json()["events"] == []


def test_replay_requires_authentication():
    resp = client.get("/v1/console/runs/run_http_3/events")
    assert resp.status_code == 401


def test_a_bad_cursor_reports_a_gap():
    resp = client.get("/v1/console/runs/run_never_existed_http/events?after=50", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["gap"] is True
