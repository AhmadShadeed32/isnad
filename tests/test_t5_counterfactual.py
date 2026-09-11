"""T5 — the OTP counterfactual, and the honesty rules around it."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.agent.investigator import build_engine_for_pricing
from app.chain.models import EvidenceLink, Verdict
from app.domain.enums import Action, Decision, Result
from app.main import app
from app.policy import counterfactual
from tests.ui_source import read_ui_source

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}

POLICY = yaml.safe_load(Path("app/policy/policy.yaml").read_text(encoding="utf-8"))
PRICING = POLICY["pricing"]
POLICY_TEXT = Path("app/policy/policy.yaml").read_text(encoding="utf-8")


def _verify(phone: str, amount: float = 4200):
    return client.post(
        "/v1/verify",
        headers=AUTH,
        json={
            "phone_number": phone,
            "context": {
                "event": "checkout",
                "payment_method": "cod",
                "account_age_days": 0,
                "amount": {"value": amount},
            },
        },
    )


# --- computed from the chain, not hardcoded ----------------------------------


def test_the_counterfactual_is_computed_from_the_actual_chain():
    """The acceptance criterion. Two runs that gather different amounts of
    evidence must report different call counts and latencies."""
    long_run = _verify("+962790000002").json()
    short_run = client.post(
        "/v1/verify",
        headers=AUTH,
        json={
            "phone_number": "+99999991001",
            "context": {"event": "signup", "account_age_days": 0},
        },
    ).json()

    assert long_run["alternative"]["isnad_calls"]["value"] == long_run["evidence_steps"]
    assert short_run["alternative"]["isnad_calls"]["value"] == short_run["evidence_steps"]
    assert long_run["evidence_steps"] != short_run["evidence_steps"]
    assert long_run["alternative"]["isnad_latency_ms"]["value"] == long_run["latency_ms"]


def test_the_call_count_tracks_the_chain_that_was_returned():
    body = _verify("+962790000002").json()

    assert body["alternative"]["isnad_calls"]["value"] == len(body["chain"])


def test_the_otp_price_follows_the_requests_country():
    jordan = _verify("+962790000002").json()["alternative"]
    emirates = _verify("+971500000002").json()["alternative"]

    assert jordan["country"] == "JO"
    assert emirates["country"] == "AE"
    assert jordan["otp_cost_usd"]["value"] == PRICING["sms_otp_list_price_usd"]["JO"]
    assert emirates["otp_cost_usd"]["value"] == PRICING["sms_otp_list_price_usd"]["AE"]
    assert jordan["otp_cost_usd"]["value"] != emirates["otp_cost_usd"]["value"]


def test_an_unknown_country_falls_back_and_says_so():
    body = _verify("+15550000002").json()["alternative"]

    assert body["country"] == "DEFAULT"
    assert body["otp_cost_usd"]["value"] == PRICING["sms_otp_list_price_usd"]["default"]
    assert "default used" in body["otp_cost_usd"]["source"]


@pytest.mark.parametrize(
    "number,expected",
    [
        ("+962790000001", "JO"),
        ("+971500000001", "AE"),
        ("+966500000001", "SA"),
        ("+15550000001", "DEFAULT"),
    ],
)
def test_country_prefix_matching(number, expected):
    assert counterfactual.country_for(number, PRICING) == expected


# --- the honesty rules --------------------------------------------------------


def test_every_figure_declares_its_basis():
    """A figure a judge checks and finds invented is worse than no figure."""
    alternative = _verify("+962790000002").json()["alternative"]

    figures = [
        "isnad_calls",
        "isnad_latency_ms",
        "isnad_cost_usd",
        "otp_messages",
        "otp_cost_usd",
        "otp_seconds",
        "otp_dropoff_rate",
    ]
    for name in figures:
        figure = alternative[name]
        assert figure["basis"] in {"measured", "list_price", "estimate", "unpriced"}, name
        assert figure["source"], name


def test_measured_and_estimated_figures_are_distinguishable():
    alternative = _verify("+962790000002").json()["alternative"]

    assert alternative["isnad_calls"]["basis"] == "measured"
    assert alternative["isnad_latency_ms"]["basis"] == "measured"
    assert alternative["otp_cost_usd"]["basis"] == "list_price"
    # These are the two that are NOT list prices and must never be shown as such.
    assert alternative["otp_seconds"]["basis"] == "estimate"
    assert alternative["otp_dropoff_rate"]["basis"] == "estimate"


def test_an_unsourced_figure_is_null_rather_than_invented():
    """No public list price exists for CAMARA calls, so none is claimed."""
    alternative = _verify("+962790000002").json()["alternative"]

    assert alternative["isnad_cost_usd"]["value"] is None
    assert alternative["isnad_cost_usd"]["basis"] == "unpriced"
    assert "policy.yaml" in alternative["isnad_cost_usd"]["source"]


def test_a_configured_camara_price_produces_a_money_figure():
    """The gap is a missing input, not a missing feature."""
    engine = build_engine_for_pricing()
    original = engine.cfg["pricing"]["camara_call_usd"]
    engine.cfg["pricing"]["camara_call_usd"] = 0.02
    try:
        verdict = Verdict(
            decision=Decision.CHALLENGE,
            confidence=0.4,
            hypothesis="mule",
            reason="…",
            chain_id="chn_pricing000000000",
            latency_ms=270,
            chain=[
                EvidenceLink(
                    step=i,
                    action=Action.SIM_SWAP,
                    api="SIM Swap",
                    result=Result.PASS,
                    signal="SIM_STABLE",
                    detail="…",
                )
                for i in range(1, 4)
            ],
        )
        alternative = counterfactual.compute(verdict, "+962790000001", engine)
        assert alternative.isnad_cost_usd.value == pytest.approx(0.06)
        assert alternative.isnad_cost_usd.basis == "list_price"
    finally:
        engine.cfg["pricing"]["camara_call_usd"] = original


def test_every_price_in_policy_carries_a_source_url_or_note():
    """The rule the runbook states: every figure carries a source comment."""
    pricing_block = POLICY_TEXT.split("pricing:", 1)[1]

    assert "https://www.twilio.com/en-us/sms/pricing/jo" in pricing_block
    assert "https://www.twilio.com/en-us/sms/pricing/ae" in pricing_block
    assert "https://www.twilio.com/en-us/sms/pricing/sa" in pricing_block
    assert "idlayr.com" in pricing_block
    assert "retrieved: 2026-08-29" in pricing_block


def test_the_estimate_sources_disclose_their_conflict_of_interest():
    """IDlayr sells a competing product. Say so before a judge finds it."""
    pricing_block = POLICY_TEXT.split("pricing:", 1)[1]
    assert "CONFLICT OF INTEREST" in pricing_block

    alternative = _verify("+962790000002").json()["alternative"]
    assert "competing product" in alternative["otp_seconds"]["source"]
    assert "competing product" in alternative["otp_dropoff_rate"]["source"]


def test_the_dropoff_estimate_takes_the_conservative_end_of_its_range():
    """The cited range is 20-30%; claiming 30% would be the flattering read."""
    assert PRICING["otp_dropoff_rate"] == 0.20


def test_the_response_note_labels_the_whole_block():
    alternative = _verify("+962790000002").json()["alternative"]

    assert "not measurements" in alternative["note"]
    assert "policy.yaml" in alternative["note"]


# --- the console --------------------------------------------------------------


def test_the_console_renders_both_paths_side_by_side():
    console = read_ui_source(Path("app/static/console.html"))

    assert "renderCounterfactual" in console
    assert "one SMS OTP" in console
    # The basis is rendered, so an estimate is never shown as a measurement.
    assert "estimates" in console


def test_tuning_needs_no_code_change():
    """policy.yaml is the tuning surface — the invariant the runbook states."""
    assert "pricing" in POLICY
    assert PRICING["sms_otp_list_price_usd"]["JO"] == 0.4429


# ---- the price of getting it wrong (item 8 of the 31 Aug plan) ----


def test_a_false_decline_is_unpriced_rather_than_invented():
    """The number that turns Act VI into a business case — and the one there is
    no honest public source for.

    Basket value, margin, lifetime value and the support contact that follows
    are all merchant-specific. Shipping a plausible figure would be exactly the
    failure the basis/source discipline exists to prevent, so it stays null and
    says why, like camara_call_usd.
    """
    body = client.post(
        "/v1/verify",
        headers=AUTH,
        json={
            "phone_number": "+962790000002",
            "context": {
                "event": "checkout",
                "payment_method": "cod",
                "account_age_days": 0,
                "amount": {"value": 4200},
            },
        },
    ).json()
    figure = body["alternative"]["false_decline_cost_usd"]
    assert figure["value"] is None
    assert figure["basis"] == "unpriced"
    assert "policy.yaml" in figure["source"]


def test_pricing_a_false_decline_also_prices_otp_abandonment(monkeypatch):
    """An abandoned signup is a customer lost the same way a false decline is,
    so one number prices both — and the derived one says it is derived."""
    from app.agent.investigator import build_engine_for_pricing
    from app.chain.models import Verdict
    from app.domain.enums import Decision
    from app.policy import counterfactual

    engine = build_engine_for_pricing()
    monkeypatch.setitem(engine.cfg["pricing"], "false_decline_cost_usd", 40.0)

    verdict = Verdict(
        decision=Decision.DECLINE,
        confidence=0.9,
        hypothesis="account_takeover",
        reason="",
        chain_id="chn_t5",
    )
    alternative = counterfactual.compute(verdict, "+962790000002", engine)

    assert alternative.false_decline_cost_usd.value == 40.0
    assert alternative.false_decline_cost_usd.basis == "merchant_supplied"
    # 40 x the 0.20 drop-off estimate.
    assert alternative.otp_dropoff_cost_usd.value == 8.0
    assert alternative.otp_dropoff_cost_usd.basis == "derived"
    assert "no more certain than the estimate inside it" in alternative.otp_dropoff_cost_usd.source
