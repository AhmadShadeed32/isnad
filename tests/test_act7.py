"""Act VII — the bank that wasn't.

Three calls, one institution, three answers. The act exists to make one point
in front of a judge: a registry hit is not trust. The same number is presented
twice, and only the announced call verifies.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.screening import LABELS

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}
CONSOLE_HTML = Path("app/static/console.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_limiters():
    """Act VII exercises several authenticated stage controls per test; their
    request count is not part of any rate-limit behaviour under test here."""
    from app.api import rate_limit

    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()
    rate_limit.per_screen.reset()
    yield
    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()
    rate_limit.per_screen.reset()


@pytest.fixture(autouse=True)
def _no_leftover_announcements():
    from app.db.database import SessionLocal
    from app.db.models import CallAnnouncementRow, ScreenEventRow

    with SessionLocal() as session:
        session.query(CallAnnouncementRow).delete()
        session.query(ScreenEventRow).delete()
        session.commit()
    yield


def _screen(target):
    return client.post(f"/v1/console/act7/screen/{target}", headers=AUTH)


def test_the_unannounced_call_is_unknown_not_safe():
    """The first beat of the act. The number really is the bank's, and that is
    worth nothing on its own — which is the line the whole demo turns on."""
    body = _screen("spoofed").json()
    assert body["label"] == "UNKNOWN"
    assert body["basis"] == "registry_match_unannounced"


def test_the_announced_call_verifies():
    client.post("/v1/console/act7/announce", headers=AUTH)
    body = _screen("announced").json()
    assert body["label"] == "VERIFIED_INSTITUTION"
    assert body["basis"] == "pre_announcement"


def test_both_beats_present_the_same_number():
    """If the two calls used different numbers the act would prove nothing —
    a judge would reasonably assume the second was simply a better number."""
    client.post("/v1/console/act7/announce", headers=AUTH)
    assert (
        _screen("spoofed").json()["caller_number"] == _screen("announced").json()["caller_number"]
    )


def test_an_announcement_to_one_customer_does_not_verify_a_call_to_another():
    """Why the spoofed beat still says UNKNOWN while an announcement is live."""
    client.post("/v1/console/act7/announce", headers=AUTH)
    assert _screen("spoofed").json()["label"] == "UNKNOWN"


def test_the_published_hotline_is_a_spoof():
    body = _screen("hotline").json()
    assert body["label"] == "SUSPECTED_SPOOF"
    assert body["basis"] == "registry_inbound_only"


def test_the_screen_is_fast_enough_to_beat_a_ring():
    body = _screen("hotline").json()
    assert body["elapsed_us"] < 100_000


def test_act_seven_requires_a_key():
    assert client.post("/v1/console/act7/announce").status_code == 401
    assert client.post("/v1/console/act7/screen/hotline").status_code == 401


def test_the_demo_announcement_does_not_speak_for_the_registered_institution():
    """The console mints a token to ANY visitor while demo mode is on, and that
    token satisfies the Act VII gate — so a stranger can create this
    announcement. An announcement records an institution asserting it is about
    to place a call, and a row written by a stranger must not carry
    `demo-bank-jo` into that record. Under a DEMO id it says what it is.
    """
    from app.db.database import SessionLocal
    from app.db.models import CallAnnouncementRow

    client.post("/v1/console/act7/announce", headers=AUTH)
    with SessionLocal() as session:
        rows = session.query(CallAnnouncementRow).all()
    assert rows
    assert all(row.institution_id != "demo-bank-jo" for row in rows)
    assert all(row.institution_id.startswith("DEMO") for row in rows)
    # The brand still shows on stage — that is what an announcement is FOR.
    assert all(row.display_name == "Demo Bank" for row in rows)


def test_an_unknown_target_404s():
    assert _screen("nonsense").status_code == 404


def test_the_stage_reset_clears_velocity_and_simulated_swaps():
    """The two demo actions share state across runs. Resetting them locally
    prevents a prior velocity burst or session demo from changing Act VII or
    Act I's first beat."""
    from app import velocity
    from app.api.routes_console import ACT7_SWITCHBOARD
    from app.providers import mock as mock_provider

    mock_provider.trip_swap("+99999991001")
    velocity.record(ACT7_SWITCHBOARD, "+962790000001")

    response = client.post("/v1/console/reset-stage", headers=AUTH)

    assert response.status_code == 200
    assert response.json()["cleared_velocity_events"] >= 1
    assert "+99999991001" not in mock_provider.TRIPPED
    assert velocity.distinct_callees(ACT7_SWITCHBOARD, 600) == 0


def test_the_console_can_run_the_caller_velocity_demo():
    """Caller velocity is the one cross-call signal in the product. It needs
    a demo control, not a terminal-only script, or it remains invisible in the
    only UI a judge sees."""
    response = client.post("/v1/console/velocity-demo", headers=AUTH)

    assert response.status_code == 200
    assert response.json()["label"] == "SUSPECTED_SPOOF"
    assert response.json()["basis"] == "caller_velocity"
    assert 'id="runVelocityDemo"' in CONSOLE_HTML


def test_the_console_defines_a_style_for_every_label_the_api_can_return():
    """Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER while
    the stylesheet only knew ALLOW/CHALLENGE/DECLINE, so the verdict panel
    stayed grey whatever the answer was. Tier 1 introduced a third vocabulary.
    This pins the two lists together so it cannot happen again.
    """
    for label in LABELS:
        assert f".verdict.{label}{{" in CONSOLE_HTML, f"no CSS rule for {label}"


def test_the_console_has_the_act_seven_control_and_handler():
    assert 'id="runAct7"' in CONSOLE_HTML
    assert "runAct7Btn.addEventListener" in CONSOLE_HTML
    # The two new event types must be rendered, or the act runs silently.
    assert "ev.type === 'screen'" in CONSOLE_HTML
    assert "ev.type === 'announce'" in CONSOLE_HTML


# ---- Act VIII — the honest limit ----


def test_act_eight_says_it_cannot_answer_rather_than_guessing():
    """A PBX trunk has no SIM, so every mobile CAMARA API is inapplicable — not
    failing. Returning TRUST_CALLER here would invent an attestation no network
    gave us; returning REJECT_CALLER would decline every real bank in the
    country. The honest answer is a chain with a hole in it.
    """
    body = client.post("/v1/console/run/act8", headers=AUTH).json()
    assert body["decision"] == "CHALLENGE"
    assert body["chain_grade"] == "UNRESOLVED"


def test_act_eight_is_registered_in_the_console():
    assert 'data-act="act8"' in CONSOLE_HTML


@pytest.mark.asyncio
async def test_the_landline_is_known_by_name_but_not_by_the_network():
    """The whole point of the act, in one assertion: the registry resolves it,
    the network cannot."""
    from app.api.routes_console import BANK_LANDLINE
    from app.api.routes_reverse import run_reverse
    from app.providers.mock import MockProvider

    verdict = await run_reverse(BANK_LANDLINE, MockProvider(), claimed_identity="Demo Bank")
    signals = [link.signal for link in verdict.chain]
    assert any(signal.startswith("REGISTRY_") for signal in signals)
    network = [link for link in verdict.chain if link.source != "local"]
    assert network and all(link.signal == "EVIDENCE_UNAVAILABLE" for link in network)
