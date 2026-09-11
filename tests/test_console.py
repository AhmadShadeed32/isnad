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
from tests.ui_source import fetch_ui_source

client = TestClient(app)

# /v1/console/run/{act} used to be unauthenticated. S4 put it behind a key: it is
# a write endpoint that persists a signed row per call, and open it let a
# stranger fire acts into the judges' console mid-presentation. The tests below
# now send the key the console itself sends. The assertions are unchanged.
AUTH = {"Authorization": "Bearer demo-merchant-key"}


@pytest.fixture(autouse=True)
def _reset_limiters():
    """These console checks deliberately make authenticated requests. Keep
    their traffic from leaking into a later file's rate-limit assertion."""
    from app.api import rate_limit

    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()
    rate_limit.per_screen.reset()
    yield
    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()
    rate_limit.per_screen.reset()


def test_console_page_serves():
    r = client.get("/console")
    assert r.status_code == 200
    assert "Isnad" in r.text
    # The stream wiring lives in the page's own script, which is now a separate
    # asset; the page is only serving correctly if that asset serves too.
    assert "/v1/console/stream" in fetch_ui_source(client, "/console")


def test_console_run_act1_allows():
    r = client.post("/v1/console/run/act1", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["decision"] == "ALLOW"


def test_console_acts_surface_their_counterfactual():
    """The Act buttons are the stage path, so T5 cannot be visible only from
    the separate forward-check button a judge is unlikely to press."""
    body = client.post("/v1/console/run/act1", headers=AUTH).json()

    assert body["alternative"]["isnad_calls"]["value"] >= 1
    assert body["alternative"]["otp_messages"]["value"] == 1


def test_console_run_unknown_act_404():
    r = client.post("/v1/console/run/nope", headers=AUTH)
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
        context=RequestContext(
            event="checkout", payment_method="cod", account_age_days=0, amount=Money(value=4200)
        ),
    )
    await build_investigator(MockProvider()).investigate(req, run_id="console-test")
    await asyncio.wait_for(task, timeout=2.0)

    assert events[0]["type"] == "start"
    assert events[-1]["type"] == "verdict"
    assert any(e["type"] == "evidence" for e in events)
    assert all(e["run_id"] == "console-test" for e in events)


def test_a_rejected_demo_token_tells_the_presenter_to_reload():
    """The console used to render an expired demo token as "Bearer API key
    required", which sends the presenter hunting for a credential when the real
    fix is a reload.

    Demo tokens live in a server-side dict with a 900s TTL, so a restart or a
    console left open past the TTL invalidates the token baked into the page.
    That is the common case on stage, and the generic message actively misleads.
    """
    page = fetch_ui_source(client, "/console")
    # The page must carry the reload instruction for both rejection codes.
    assert "demo session expired" in page
    assert "reload the page" in page
    # And it must not have regressed to the bare server message as the only
    # thing a presenter sees.
    assert "authFailureMessage" in page


def test_an_unknown_demo_token_is_refused():
    """The message above is only reachable if the server actually rejects a
    stale token rather than honouring it."""
    r = client.get("/v1/console/mode", headers={"Authorization": "Bearer demo_not_a_real_token"})
    assert r.status_code in (401, 403)


def test_a_rejected_operator_key_is_cleared_rather_than_retried_forever():
    """apiKey() reads sessionStorage, and requireApiKey() only prompts when the
    stored value is empty — so a wrong merchant key used to wedge the tab until
    it was closed. The handler drops it on rejection."""
    page = fetch_ui_source(client, "/console")
    assert "sessionStorage.removeItem(TOKEN_KEY)" in page


def test_the_act_buttons_send_a_credential():
    """S4 put /v1/console/run/{act} behind a key, but the console kept calling it
    with `auth:false`. Every Act button and the full-stage run 401ed before the
    investigator started, which also left the ask-the-agent box disabled because
    setLatestChain() never ran on that path."""
    page = fetch_ui_source(client, "/console")
    assert "auth:false, headers:{'X-Console-Run-Id'" not in page


def test_reverse_isnad_verdicts_are_styled():
    """Reverse Isnad returns TRUST_CALLER / CAUTION / REJECT_CALLER, not the
    forward flow's ALLOW / CHALLENGE / DECLINE, and setVerdict() sets the class
    directly — so without these rules the panel stays grey whatever the answer."""
    page = fetch_ui_source(client, "/console")
    for cls in ("TRUST_CALLER", "CAUTION", "REJECT_CALLER"):
        assert f".verdict.{cls}{{" in page, f"no style for {cls}"


def test_the_planner_pill_is_set_from_server_mode_on_page_load():
    """Until the first verdict, the pill read `planner: —` even though the
    authenticated mode endpoint already returns the planner."""
    page = fetch_ui_source(client, "/console")

    assert "setPlannerBadge(health.planner);" in page


def test_the_console_labels_unpriced_rows_and_the_default_country():
    """An em dash looks like a rendering defect in a live demo, not the
    deliberate absence of a merchant-specific price."""
    page = fetch_ui_source(client, "/console")

    assert "not priced — merchant-specific" in page
    assert "regional default list price" in page


def test_the_deployment_serve_target_trusts_proxy_headers_for_receipt_qrs():
    """Behind a TLS-terminating tunnel, receipt_qr must see the forwarded
    scheme or it embeds an unusable http:// URL in the QR code."""
    with open("Makefile", encoding="utf-8") as makefile:
        contents = makefile.read()

    assert "--proxy-headers" in contents


def test_the_mode_reports_the_planner_that_will_actually_run(monkeypatch):
    """`configureMode()` sets the planner pill from /v1/console/mode at page
    load, before any investigation row has arrived to correct it. But
    `settings.planner` is a request, not an outcome: `LLMPlanner` falls straight
    through to greedy whenever `_maybe_client` finds no key, and the pill would
    then read a green `llm` above a run greedy is choosing. The pill is the one
    thing on the console that claims the agent is real, so it is the one claim a
    judge is most likely to test."""
    from app.config import settings

    monkeypatch.setattr(settings, "planner", "llm")
    monkeypatch.setattr(settings, "gemini_api_key", None)
    assert client.get("/v1/console/mode", headers=AUTH).json()["planner"] == "greedy"

    # And it must still say `llm` when the key is there, or the fix is just a
    # constant that hides the agent instead of reporting it.
    monkeypatch.setattr(settings, "gemini_api_key", "a-configured-key")
    assert client.get("/v1/console/mode", headers=AUTH).json()["planner"] == "llm"
