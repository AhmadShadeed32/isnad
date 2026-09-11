"""Number Recycling: continuity checked before stored trust is reused.

The check exists for one situation — a merchant about to rely on a phone number
it verified some time ago. So the merchant's own last-verified date is what makes
the question askable, and everything here follows from that: no date means no
question, a date the operator cannot answer means unknown, and a number that was
*not* recycled removes a doubt without buying anything.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.agent.investigator import build_investigator
from app.agent.planner import _UNSERVED, GreedyPlanner
from app.domain.enums import Action, Result
from app.domain.schemas import RequestContext, VerificationRequest
from app.main import app
from app.policy.engine import get_engine
from app.providers.mock import MockProvider

AUTH = {"Authorization": "Bearer demo-merchant-key"}
RECYCLED_NUMBER = "+962790000002"   # the takeover fixture
CONTINUOUS_NUMBER = "+962790000006"  # the lost-phone fixture: same customer
UNAVAILABLE_NUMBER = "+962790000005"  # the gap fixture: operator cannot answer
LAST_YEAR = date(2026, 1, 15)


@pytest.fixture
def unlimited(monkeypatch):
    """The suite shares one rate-limit bucket per key, so a test that happens to
    run late gets a 429 that has nothing to do with what it is checking."""
    from app.config import settings

    monkeypatch.setattr(settings, "rate_limit_enabled", False, False)


def _engine():
    from app.config import settings

    return get_engine(str(settings.policy_path))


def _run(number: str, *, last_verified_at: date | None = LAST_YEAR, provider=None):
    request = VerificationRequest(
        phone_number=number,
        context=RequestContext(
            event="checkout", account_age_days=400, last_verified_at=last_verified_at
        ),
    )
    investigator = build_investigator(provider or MockProvider())
    return asyncio.run(investigator.investigate(request))


def _link(verdict):
    found = [link for link in verdict.chain if link.action == Action.NUMBER_RECYCLING]
    return found[0] if found else None


# --- the two real answers ----------------------------------------------------


def test_a_recycled_number_is_adverse_evidence():
    """The SIM this merchant once verified now belongs to someone else, so the
    trust it stored in this number is void."""
    link = _link(_run(RECYCLED_NUMBER))

    assert link is not None
    assert link.signal == "NUMBER_RECYCLED"
    assert link.result == Result.FLAG
    assert link.delta_logodds > 0


def test_a_continuous_number_is_recorded_but_buys_nothing():
    link = _link(_run(CONTINUOUS_NUMBER))

    assert link.signal == "NUMBER_CONTINUOUS"
    assert link.result == Result.PASS
    # Exactly zero. "The subscriber did not change" removes a doubt; it does not
    # attest that this person is who they say they are.
    assert link.delta_logodds == 0.0


def test_a_non_recycled_number_can_never_satisfy_the_allow_gate():
    """The gate counts only strictly-negative links as support, and this one is
    weighted at zero — so "not recycled" cannot, by itself, produce an ALLOW."""
    engine = _engine()

    assert engine.signal_delta("NUMBER_CONTINUOUS") == 0.0
    assert Action.NUMBER_RECYCLING in engine.cfg["hypotheses"]["account_takeover"]["relevant"]


def test_a_recycled_number_triggers_fresh_verification_whatever_else_says():
    """Not a weight to be outweighed. The merchant was about to rely on trust it
    stored earlier, and the operator says that trust is about somebody else."""
    verdict = _run(RECYCLED_NUMBER)

    assert verdict.decision.value in {"CHALLENGE", "DECLINE"}


def test_the_recycling_block_is_not_disguised_as_a_failed_check():
    """It is a definite answer, not a hole in the chain: the receipt must not
    say the operator could not tell us something it told us plainly."""
    from app.agent.investigator import _UNRESOLVED_SIGNALS

    assert "NUMBER_RECYCLED" not in _UNRESOLVED_SIGNALS


# --- the precondition --------------------------------------------------------


def test_without_a_merchant_reference_date_the_check_never_runs():
    """No prior verification is a reason not to ask, not a reason to guess a
    date. A signup date invented by the backend would make this check answer a
    question nobody asked, confidently."""
    verdict = _run(RECYCLED_NUMBER, last_verified_at=None)

    assert _link(verdict) is None


def test_no_provider_call_is_made_without_a_reference_date():
    class Watching(MockProvider):
        def __init__(self):
            super().__init__()
            self.recycling_calls = 0

        async def gather(self, action, request):
            if action == Action.NUMBER_RECYCLING:
                self.recycling_calls += 1
            return await super().gather(action, request)

    provider = Watching()
    _run(RECYCLED_NUMBER, last_verified_at=None, provider=provider)

    assert provider.recycling_calls == 0


def test_without_a_reference_date_nothing_is_charged_for_it():
    with_date = _run(CONTINUOUS_NUMBER)
    without = _run(CONTINUOUS_NUMBER, last_verified_at=None)

    assert with_date.evidence_cost - without.evidence_cost == pytest.approx(
        _engine().action_cost(Action.NUMBER_RECYCLING)
    )


def test_a_future_reference_date_is_unknown_rather_than_a_result():
    """Observed 2026-09-06: the hosted simulator answers 400 to a future
    reference date. A merchant's bad input reads as unknown, not as an outage
    and never as "not recycled"."""
    tomorrow = datetime.now(UTC).date() + timedelta(days=1)
    link = _link(_run(CONTINUOUS_NUMBER, last_verified_at=tomorrow))

    assert link.signal == "RECYCLING_REFERENCE_INVALID"
    assert link.result == Result.INFO
    assert link.delta_logodds == 0.0


def test_a_far_future_reference_date_is_also_refused():
    link = _link(_run(CONTINUOUS_NUMBER, last_verified_at=date(2099, 1, 1)))

    assert link.signal == "RECYCLING_REFERENCE_INVALID"


def test_an_unparseable_reference_date_is_rejected_by_the_schema(unlimited):
    client = TestClient(app)
    response = client.post(
        "/v1/verify",
        headers=AUTH,
        json={
            "phone_number": CONTINUOUS_NUMBER,
            "context": {"event": "checkout", "last_verified_at": "the day before yesterday"},
        },
    )

    assert response.status_code == 422


def test_an_unavailable_service_is_a_hole_not_a_finding():
    link = _link(_run(UNAVAILABLE_NUMBER))

    assert link.signal == "EVIDENCE_UNAVAILABLE"
    assert link.result == Result.INFO
    assert link.delta_logodds == 0.0


def test_an_unavailable_recycling_result_never_becomes_an_allow():
    verdict = _run(UNAVAILABLE_NUMBER)

    assert verdict.decision.value != "ALLOW"


# --- it is choreographed, never chosen ---------------------------------------


def test_the_planner_can_never_select_this_check():
    """It is the cheapest check priced. A planner that could reach it would buy
    it first on every request and get "no reference date" for the money."""
    assert Action.NUMBER_RECYCLING in _UNSERVED

    greedy = GreedyPlanner(_engine())
    assert Action.NUMBER_RECYCLING not in greedy.affordable(set(), 99)


def test_the_check_is_choreography_and_the_trace_says_so():
    """The signed `planner` field's vocabulary is llm/greedy, so the label for
    this step lives in the emitted selection event instead."""
    events: list[dict] = []

    async def sink(event):
        events.append(event)

    investigator = build_investigator(MockProvider(), event_sink=sink)
    asyncio.run(
        investigator.investigate(
            VerificationRequest(
                phone_number=RECYCLED_NUMBER,
                context=RequestContext(
                    event="checkout", account_age_days=400, last_verified_at=LAST_YEAR
                ),
            )
        )
    )
    continuity = [e for e in events if e.get("phase") == "continuity"]

    assert continuity, [e.get("phase") for e in events]
    assert continuity[0]["planner"] == "policy"
    assert continuity[0]["api"] == "Number Recycling"


def test_it_runs_before_the_evidence_the_planner_buys():
    """Continuity is asked before stored trust is reused, not after."""
    verdict = _run(RECYCLED_NUMBER)
    steps = {link.action: link.step for link in verdict.chain}

    assert steps[Action.NUMBER_RECYCLING] == min(steps.values())


def test_it_is_charged_within_the_same_budget_as_every_other_call():
    verdict = _run(CONTINUOUS_NUMBER)
    engine = _engine()
    expected = sum(engine.action_cost(link.action) for link in verdict.chain)
    enrichments = sum(
        engine.enrichment_cost("swap_date")
        for link in verdict.chain
        if link.timing is not None and link.timing.availability != "unsupported"
    )

    assert verdict.evidence_cost == pytest.approx(expected + enrichments)


def test_a_budget_too_small_skips_it_rather_than_overspending():
    engine = _engine()
    original = engine.cfg["budget"]
    try:
        engine.cfg["budget"] = {"default": 0.5}
        verdict = _run(CONTINUOUS_NUMBER)
    finally:
        engine.cfg["budget"] = original

    assert _link(verdict) is None


# --- tenancy and idempotency -------------------------------------------------


def test_the_reference_date_is_part_of_the_request_commitment():
    """Two requests that differ only in the reference date are different
    questions, so they must not share a cached answer."""
    from app.chain.subject import request_commitment

    def commitment(reference: str):
        return request_commitment(
            VerificationRequest(
                phone_number=CONTINUOUS_NUMBER,
                context=RequestContext(event="checkout", last_verified_at=date.fromisoformat(reference)),
            )
        )

    assert commitment("2026-01-15") != commitment("2025-01-15")


def test_the_same_body_from_two_merchants_produces_two_chains(unlimited):
    client = TestClient(app)
    body = {
        "phone_number": CONTINUOUS_NUMBER,
        "context": {"event": "checkout", "last_verified_at": LAST_YEAR.isoformat()},
    }
    first = client.post("/v1/verify", headers=AUTH, json=body).json()
    second = client.post(
        "/v1/verify", headers={"Authorization": "Bearer demo-merchant-key"}, json=body
    ).json()

    assert first["chain_id"] != second["chain_id"]


def test_a_recycling_link_survives_into_the_signed_chain(unlimited):
    client = TestClient(app)
    response = client.post(
        "/v1/verify",
        headers=AUTH,
        json={
            "phone_number": RECYCLED_NUMBER,
            "context": {
                "event": "checkout",
                "account_age_days": 400,
                "last_verified_at": LAST_YEAR.isoformat(),
            },
        },
    )

    assert response.status_code == 200, response.text
    signals = [link["signal"] for link in response.json()["chain"]]
    assert "NUMBER_RECYCLED" in signals


# --- the sentence it is allowed to say ---------------------------------------


@pytest.mark.parametrize(
    "signal",
    [
        "NUMBER_RECYCLED",
        "NUMBER_CONTINUOUS",
        "RECYCLING_REFERENCE_MISSING",
        "RECYCLING_REFERENCE_INVALID",
    ],
)
def test_every_recycling_signal_has_an_authored_sentence(signal):
    from app.providers.vocabulary import SPEAKABLE_SIGNALS, detail_for

    assert signal in SPEAKABLE_SIGNALS
    assert detail_for(signal)


def test_no_recycling_sentence_claims_fraud():
    """A recycled number means the merchant's stored trust is stale. It does not
    mean the current holder is doing anything wrong."""
    from app.providers.vocabulary import detail_for

    for signal in ("NUMBER_RECYCLED", "NUMBER_CONTINUOUS"):
        sentence = detail_for(signal).lower()
        assert "fraud" not in sentence
        assert "attack" not in sentence
