"""I14's HTTP surface: GET /v1/console/runs/{run_id}/events.

Authorized the same way every other console route is -- through
require_api_key -- never derived from the run_id alone, which a client
could simply guess or copy from another tenant's own console session.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.events import current_owner, emit
from app.main import app
from tests.ui_source import read_ui_source

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


# --- the live event carries the sequence the journal assigned -----------------


async def _delivered(events: list[dict]) -> list[dict]:
    """Emit each event and return what a subscriber actually received.

    `emit` redacts into a copy, so it never mutates its caller's dict — the
    sequence has to be observed on the delivered event, which is the only
    place a browser would ever see it.
    """
    import asyncio

    from app.events import subscribe
    from app.ownership import owner_hash

    owner = owner_hash("demo-merchant-key")
    token = current_owner.set(owner)
    try:
        stream = subscribe(owner)
        received: list[dict] = []

        async def collect():
            async for event in stream:
                received.append(event)
                if len(received) == len(events):
                    break

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.05)
        for event in events:
            await emit(event)
        await asyncio.wait_for(task, timeout=3)
        return received
    finally:
        current_owner.reset(token)


@pytest.mark.asyncio
async def test_a_live_event_carries_its_journal_sequence():
    """At-least-once means the same event legitimately arrives twice — once
    live, once replayed. Without a shared key the UI cannot tell that the two
    deliveries are the same event, so it would either double-render or drop
    something real."""
    received = await _delivered([
        {"type": "start", "run_id": "run-seq-live", "hypothesis": "legit"},
        {"type": "verdict", "run_id": "run-seq-live", "decision": "ALLOW"},
    ])
    assert [e["sequence"] for e in received] == [1, 2]


@pytest.mark.asyncio
async def test_an_event_that_failed_to_persist_carries_no_sequence(monkeypatch):
    """Numbering a live-only event as if it were in the journal would promise
    a recovery that cannot happen."""
    from app.db import run_events

    monkeypatch.setattr(run_events, "persist_event", lambda *a, **k: None)
    received = await _delivered([{"type": "start", "run_id": "run-seq-none", "hypothesis": "x"}])
    assert "sequence" not in received[0]


@pytest.mark.asyncio
async def test_an_event_with_no_run_id_is_never_numbered():
    """Most emissions carry no run_id and are not replayable at all."""
    received = await _delivered([{"type": "screen", "label": "VERIFIED_INSTITUTION"}])
    assert "sequence" not in received[0]


@pytest.mark.asyncio
async def test_the_replayed_sequence_matches_the_live_one():
    """The two deliveries have to agree, or deduplication is meaningless."""
    received = await _delivered([{"type": "start", "run_id": "run-seq-match", "hypothesis": "x"}])
    replayed = client.get("/v1/console/runs/run-seq-match/events?after=0", headers=AUTH).json()
    assert [row["sequence"] for row in replayed["events"]] == [received[0]["sequence"]]


# --- the console's own recovery control ---------------------------------------

CONSOLE_HTML = read_ui_source(Path("app/static/console.html"))
CONSOLE_SCRIPT = CONSOLE_HTML.split("<script>")[-1].split("</script>")[0]


def test_the_console_offers_a_recovery_control():
    assert 'id="recoverBtn"' in CONSOLE_HTML
    assert "recoverBtn.addEventListener('click', recoverMissedEvents);" in CONSOLE_SCRIPT


def test_the_console_deduplicates_by_sequence():
    assert "seenSequences.has(ev.sequence)) return;" in CONSOLE_SCRIPT
    assert "if (seenSequences.has(row.sequence)) continue;" in CONSOLE_SCRIPT


def test_recovery_asks_only_for_what_it_has_not_seen():
    assert "'/events?after=' + encodeURIComponent(highestSequence)" in CONSOLE_SCRIPT


def test_a_new_run_starts_a_clean_recovery_state():
    """Sequences restart per run, so a previous run's numbers must not suppress
    this one's events."""
    assert "resetRecovery();" in CONSOLE_SCRIPT
    assert "seenSequences = new Set();" in CONSOLE_SCRIPT


def test_a_retention_gap_is_announced_and_never_filled_in():
    assert "if (data.gap){" in CONSOLE_SCRIPT
    assert "nothing here reconstructs the absent events" in CONSOLE_SCRIPT
    assert 'recoverNote.className = \'recover-note gap\';' in CONSOLE_SCRIPT


def test_recovery_says_it_bought_no_checks():
    """I14's bound: the journal resumes the record of a run, never the run."""
    assert "No provider call was made." in CONSOLE_SCRIPT
    assert "resumes the *record* of a run, never the run" in CONSOLE_SCRIPT


def test_a_dropped_stream_tells_the_operator_recovery_exists():
    assert "The evidence stream dropped." in CONSOLE_SCRIPT


def test_the_console_never_invents_a_missing_detail_string():
    """The journal's allowlist excludes provider prose on purpose, so a
    replayed evidence row falls back to the normalized signal rather than to a
    sentence written at replay time."""
    assert "const said = ev.detail || ev.signal || '(not journalled)';" in CONSOLE_SCRIPT
    from app.db.run_events import _ALLOWED_BODY_KEYS

    assert "detail" not in _ALLOWED_BODY_KEYS


def test_a_recovered_row_never_renders_undefined():
    """Every field the journal may not hold goes through `val`, which names
    the absence. Printing "undefined" was the actual bug; filling the field in
    would have been the worse one."""
    assert "function val(v, absent){" in CONSOLE_SCRIPT
    assert "'(not journalled)'" in CONSOLE_SCRIPT
    for field in ("ev.label", "ev.reason", "ev.basis", "ev.elapsed_us",
                  "ev.announcement_id", "ev.calls", "ev.threshold"):
        assert f"val({field}" in CONSOLE_SCRIPT, field


def test_a_recovered_row_says_it_was_recovered():
    assert CONSOLE_SCRIPT.count("ev.replayed ? ' · recovered' : ''") >= 4


@pytest.mark.asyncio
async def test_the_journal_keeps_no_subscriber_number():
    """The Verified Caller act emits the calling number. A journal outlives the
    request that made it, and a masked number is still not one to keep."""
    from app.db import run_events
    from app.ownership import owner_hash

    token = current_owner.set(owner_hash("demo-merchant-key"))
    try:
        await emit({
            "type": "announce",
            "run_id": "run-no-numbers",
            "institution": "Demo Bank",
            "calling_participant": "+96265000000",
            "caller_number": "+962790000002",
            "announcement_id": "ann_1",
            "ttl_seconds": 120,
        })
    finally:
        current_owner.reset(token)

    rows = run_events.events_after(owner_hash("demo-merchant-key"), "run-no-numbers", after=0)
    assert rows
    body = rows[0]["body"]
    assert "calling_participant" not in body
    assert "caller_number" not in body
    assert "+9626" not in json.dumps(body)
    # And the fields that make the row readable did survive.
    assert body["institution"] == "Demo Bank"
    assert body["announcement_id"] == "ann_1"


def test_the_journal_still_refuses_provider_prose():
    """`detail` is the one field on an evidence event that an operator writes.
    Widening the allowlist for the caller acts must not have let it in."""
    from app.db.run_events import _ALLOWED_BODY_KEYS

    for forbidden in ("detail", "caller_number", "calling_participant",
                      "phone_number", "prompt", "stream_token"):
        assert forbidden not in _ALLOWED_BODY_KEYS, forbidden


def test_a_recovered_row_is_stamped_with_the_time_it_was_recorded():
    """It did not happen now. An elapsed-since-start figure would be a made-up
    number, and before a run starts it was measured from the epoch."""
    assert "replayTime = journalTime(row.server_time);" in CONSOLE_SCRIPT
    assert "if (replayTime) return replayTime;" in CONSOLE_SCRIPT
    assert "if (!t0) return '--.--';" in CONSOLE_SCRIPT


def test_the_journal_row_carries_the_server_time_the_console_stamps_with():
    """The console cannot stamp a recovered row with a real time unless the
    journal hands one over."""
    rows = client.get("/v1/console/runs/run-seq-match/events?after=0", headers=AUTH).json()["events"]
    assert rows
    datetime.fromisoformat(rows[0]["server_time"])  # parses, or the page shows --.--
