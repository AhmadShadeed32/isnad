"""chain_grade — what the chain itself was worth, beside what the caller should do.

The pair that has to hold under scrutiny is UNRESOLVED vs DEGRADED: an
unobtainable link and a failed check are different facts, and a judge (or an
auditor) should be able to tell them apart from the response body alone.
"""

from __future__ import annotations

import pytest

from app.agent.investigator import build_investigator
from app.agent.planner import Choice, GreedyPlanner
from app.config import settings
from app.domain.enums import Action, ChainGrade, Decision, Hypothesis
from app.domain.schemas import Money, RequestContext, VerificationRequest
from app.policy.engine import get_engine
from app.providers.mock import MockProvider


def _engine():
    return get_engine(str(settings.policy_path))


def _investigator():
    return build_investigator(MockProvider())


# Act VI — the lost phone. The customer replaced a SIM three days ago and is
# otherwise exactly where and who they should be.
_ACT6 = VerificationRequest(
    phone_number="+99999991006",
    context=RequestContext(
        event="checkout",
        payment_method="cod",
        account_age_days=0,
        amount=Money(value=1500),
    ),
)


# ---- the derivation, branch by branch ----


def test_unresolved_wins_even_when_the_rest_looks_clean():
    """A chain with a hole in it was never fully attested, however clean the
    remaining evidence reads. This is the branch that prevents a false ALLOW."""
    grade = _engine().grade(
        p_fraud=0.02,
        unresolved=True,
        link_deltas=[-1.2, -0.8, -0.5],
        hypothesis=Hypothesis.LEGIT,
    )
    assert grade == ChainGrade.UNRESOLVED


def test_an_empty_chain_is_unresolved_in_every_band():
    """It graded ATTESTED_PARTIAL — "the links resolved and nothing contradicted
    the claim" — of ZERO links, and rendered green in the console beside a
    verdict resting on no evidence at all. Every grade below the branch is a
    claim about links, so the branch sits above the band checks: REFUTED would
    have claimed "a link directly contradicts" and DEGRADED "one or more came
    back adverse", of the same zero links.
    """
    engine = _engine()
    for p_fraud in (0.02, 0.5, 0.95):
        grade = engine.grade(
            p_fraud=p_fraud,
            unresolved=False,
            link_deltas=[],
            hypothesis=Hypothesis.LEGIT,
        )
        assert grade == ChainGrade.UNRESOLVED, p_fraud


def test_a_chain_of_only_neutral_links_is_not_an_empty_chain():
    """The boundary the fix must not move. Local evidence is priced at 0.0 —
    REGISTRY_MATCH_UNANNOUNCED, REGISTRY_UNLISTED — so a chain of real links
    that moved belief by nothing still HAPPENED, and grades on the normal path.
    """
    engine = _engine()
    assert (
        engine.grade(
            p_fraud=0.02,
            unresolved=False,
            link_deltas=[0.0, 0.0],
            hypothesis=Hypothesis.LEGIT,
        )
        == ChainGrade.ATTESTED_FULL
    )


def test_refuted_above_the_decline_threshold():
    grade = _engine().grade(
        p_fraud=0.95,
        unresolved=False,
        link_deltas=[2.2, 1.6],
        hypothesis=Hypothesis.ACCOUNT_TAKEOVER,
    )
    assert grade == ChainGrade.REFUTED


def test_degraded_in_the_uncertain_band():
    grade = _engine().grade(
        p_fraud=0.5,
        unresolved=False,
        link_deltas=[1.6, -0.5],
        hypothesis=Hypothesis.MULE,
    )
    assert grade == ChainGrade.DEGRADED


def test_attested_full_needs_enough_corroborating_links():
    e = _engine()
    hyp = Hypothesis.ACCOUNT_TAKEOVER
    n = e.min_links_for(hyp)
    clean = [-1.0] * n
    assert e.grade(0.02, False, clean, hyp) == ChainGrade.ATTESTED_FULL
    # One link short of the bar is attested, but only partially.
    assert e.grade(0.02, False, clean[:-1], hyp) == ChainGrade.ATTESTED_PARTIAL


def test_an_adverse_link_downgrades_a_clean_verdict_to_partial():
    """Belief cleared overall, but one check pushed toward fraud — that chain is
    not fully attested even though the customer is allowed through."""
    e = _engine()
    adverse = e.adverse_delta()
    deltas = [-1.2, -0.8, adverse + 0.1]
    assert e.grade(0.10, False, deltas, Hypothesis.LEGIT) == ChainGrade.ATTESTED_PARTIAL


def test_min_links_falls_back_to_the_default_for_an_unknown_hypothesis():
    e = _engine()
    assert e.min_links_for("something_not_in_policy") == e.cfg["grading"]["default_min_links"]


# ---- the attestation gate counts SUPPORTING network facts ----


def _link(source: str, delta: float):
    from app.chain.models import EvidenceLink
    from app.domain.enums import API_LABEL, Result

    return EvidenceLink(
        step=1,
        action=Action.NUMBER_VERIFY,
        api=API_LABEL[Action.NUMBER_VERIFY],
        result=Result.PASS,
        signal="X",
        detail="x",
        source=source,
        delta_logodds=delta,
    )


def _gate(links) -> bool:
    from app.agent.belief import Belief
    from app.chain.models import Chain
    from app.policy.engine import p_to_logodds

    chain = Chain(id="chn_test000000000000")
    chain.links = list(links)
    belief = Belief(logodds=p_to_logodds(0.02))  # decisively clean
    return _investigator()._needs_a_network_fact(belief, chain)


def test_an_adverse_network_link_does_not_satisfy_the_attestation_gate():
    """The gate exists so a stolen key is not an instant pass. It counted
    network links by PRESENCE, so an announcement (-2.5) plus a contradicting
    NUMBER_MISMATCH (+1.5) satisfied it — belief still cleared the threshold,
    and the announcement had bought a pass past the evidence against it.

    It held under greedy, which never stops, and failed under any planner that
    stops once belief is decisive — which is what the LLM planner's prompt tells
    it to do. Same trap as C1.
    """
    announced = _link("local", -2.5)
    assert _gate([announced]) is True, "local evidence alone must not stop the agent"
    assert _gate([announced, _link("mock", 1.5)]) is True, "an adverse fact is not attestation"
    assert _gate([announced, _link("mock", -1.2)]) is False, "a supporting fact satisfies it"
    # The neutral boundary, and it is NOT covered by anything else: a 0.0 link
    # is the could-not-check family (LOCATION_UNKNOWN, LOCATION_PARTIAL, and the
    # mock's catch-all), and only CONSENT_REQUIRED / PROVIDER_UNAVAILABLE /
    # EVIDENCE_UNAVAILABLE are in _UNRESOLVED_SIGNALS — so the ALLOW->CHALLENGE
    # conversion does not catch this one. A link that moved belief by nothing
    # attests nothing.
    assert _gate([announced, _link("mock", 0.0)]) is True, "zero information is not attestation"


# ---- end to end, through the real engine ----


@pytest.mark.asyncio
async def test_clean_signup_is_attested_and_allowed():
    """A clean chain clears, and the grade says which kind of clean it was.

    The grade assertion used to accept EITHER attested value, which is every
    grade a cleared chain can hold — it could not fail while the verdict
    allowed. It now pins the one the policy actually produces, so a change in
    `min_links` or `adverse_delta` shows up here instead of passing quietly.
    """
    req = VerificationRequest(
        phone_number="+962790000001",
        context=RequestContext(event="signup", account_age_days=0),
    )
    verdict = await _investigator().investigate(req)
    assert verdict.decision == Decision.ALLOW
    assert verdict.chain_grade == ChainGrade.ATTESTED_PARTIAL
    # Which is the honest grade for this chain, and here is why: it cleared on
    # ONE link, and full attestation asks for `min_links` corroborating facts.
    assert len(verdict.chain) < _engine().min_links_for(verdict.hypothesis)
    assert all(link.delta_logodds < _engine().adverse_delta() for link in verdict.chain)


@pytest.mark.asyncio
async def test_takeover_declines_and_grades_refuted():
    req = VerificationRequest(
        phone_number="+962790000002",
        context=RequestContext(
            event="checkout",
            payment_method="cod",
            account_age_days=0,
            amount=Money(value=4200),
        ),
    )
    verdict = await _investigator().investigate(req)
    assert verdict.decision == Decision.DECLINE
    assert verdict.chain_grade == ChainGrade.REFUTED


@pytest.mark.asyncio
async def test_grade_is_inside_the_signed_payload():
    """The grade must be as tamper-evident as the decision it sits beside."""
    from app.chain.vault import vault
    from app.db import store

    req = VerificationRequest(
        phone_number="+962790000001",
        context=RequestContext(event="signup", account_age_days=0),
    )
    verdict = await _investigator().investigate(req)
    record = store.save(verdict)
    assert '"chain_grade"' in record.verdict_json
    assert vault.verify(record.verdict_json.encode("utf-8"), record.signature)
    swapped = (
        ChainGrade.REFUTED.value
        if verdict.chain_grade is not ChainGrade.REFUTED
        else ChainGrade.ATTESTED_FULL.value
    )
    tampered = record.verdict_json.replace(
        f'"chain_grade":"{verdict.chain_grade.value}"', f'"chain_grade":"{swapped}"'
    )
    assert tampered != record.verdict_json, "grade should be present as its own JSON field"
    assert not vault.verify(tampered.encode("utf-8"), record.signature)


def test_verify_endpoint_returns_the_grade():
    """A caller reading only the response body can tell a hole in the chain from
    a failed check — without parsing the reason string."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.post(
        "/v1/verify",
        headers={"Authorization": "Bearer demo-merchant-key"},
        json={
            "phone_number": "+962790000002",
            "context": {
                "event": "checkout",
                "payment_method": "cod",
                "account_age_days": 0,
                "amount": {"value": 4200},
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "DECLINE"
    assert body["chain_grade"] == ChainGrade.REFUTED.value


# ---- the two acts that exist to make the grade visible on stage ----


@pytest.mark.asyncio
async def test_act5_consent_withheld_is_unresolved_not_declined():
    """The differentiator: a chain with a hole in it is a step-up, not a refusal.
    Collapsing this into DECLINE is what manufactures false declines."""
    req = VerificationRequest(
        phone_number="+99999991005",
        context=RequestContext(
            event="checkout",
            payment_method="cod",
            account_age_days=0,
            amount=Money(value=900),
        ),
    )
    verdict = await _investigator().investigate(req)
    assert verdict.decision == Decision.CHALLENGE
    assert verdict.chain_grade == ChainGrade.UNRESOLVED
    assert any(
        link.signal in {"CONSENT_REQUIRED", "PROVIDER_UNAVAILABLE", "EVIDENCE_UNAVAILABLE"}
        for link in verdict.chain
    )


@pytest.mark.asyncio
async def test_act6_a_real_sim_replacement_is_degraded_not_refuted():
    """SIM_SWAPPED alone is not fraud. The agent keeps investigating, finds the
    same handset at the claimed address, and steps up instead of declining."""
    verdict = await _investigator().investigate(_ACT6)
    assert verdict.decision == Decision.CHALLENGE
    assert verdict.chain_grade == ChainGrade.DEGRADED
    signals = [link.signal for link in verdict.chain]
    assert "SIM_SWAPPED" in signals  # the signal a rules engine would decline on
    assert "DEVICE_STABLE" in signals  # the corroboration that saves the customer


class _SwapFirstPlanner:
    """A planner that opens on the SIM swap, as the LLM planner is free to do.

    This is the order the greedy planner never produces: greedy opens with
    number_verify, whose -1.2 holds belief under the decline threshold long
    enough for the rest of the chain to be gathered. So the act6 case above
    passed while the live console — running ISNAD_PLANNER=llm — declined the
    same customer off one check. The bug was an ordering dependency, and only a
    planner that picks a different order can see it.
    """

    source = "llm"

    def __init__(self, engine):
        self.engine = engine

    def choose(self, hypothesis, used, budget_left, p_fraud, observations):
        if Action.SIM_SWAP not in used:
            return Choice(Action.SIM_SWAP, "stub: open on the swap", self.source)
        return Choice(None, "stub: nothing further to ask", self.source)

    def next_best(self, hypothesis, used, budget_left):
        return None

    def cheapest_stepup(self, used, budget_left):
        return GreedyPlanner(self.engine).cheapest_stepup(used, budget_left)


@pytest.mark.asyncio
async def test_act6_is_not_declined_when_the_planner_opens_on_the_swap():
    """SIM_SWAPPED alone must not carry a decline, whatever order it arrives in.

    Policy names the checks that could still exonerate; the agent runs them
    before it is allowed to stop, so the verdict no longer depends on which
    action the planner happened to pick first.
    """
    inv = _investigator()
    inv.planner = _SwapFirstPlanner(inv.engine)
    verdict = await inv.investigate(_ACT6)

    assert verdict.decision == Decision.CHALLENGE
    assert verdict.chain_grade == ChainGrade.DEGRADED

    signals = [link.signal for link in verdict.chain]
    assert signals[0] == "SIM_SWAPPED"  # the planner still opened on the swap
    assert "DEVICE_STABLE" in signals  # same handset across the swap
    assert "AT_CLAIMED_LOCATION" in signals  # and still at the usual place


@pytest.mark.asyncio
async def test_a_real_takeover_still_declines_after_corroboration():
    """The corroboration must not become a way out of a genuine takeover.

    Act II answers the same two checks the other way — new handset, wrong
    location — so gathering them drives belief up, not down.
    """
    inv = _investigator()
    inv.planner = _SwapFirstPlanner(inv.engine)
    req = VerificationRequest(
        phone_number="+99999991000",
        context=RequestContext(
            event="checkout",
            payment_method="cod",
            account_age_days=0,
            amount=Money(value=4200),
        ),
    )
    verdict = await inv.investigate(req)

    assert verdict.decision == Decision.DECLINE
    assert verdict.chain_grade == ChainGrade.REFUTED
    signals = [link.signal for link in verdict.chain]
    assert "DEVICE_SWAPPED" in signals and "NOT_AT_CLAIMED_LOCATION" in signals


def test_corroboration_only_gates_the_decline_side():
    """A chain that clears stops when it clears and pays for nothing extra."""
    e = _engine()
    assert e.corroboration_for("SIM_SWAPPED") == [Action.DEVICE_SWAP, Action.LOCATION_VERIFY]
    assert e.corroboration_for("SIM_STABLE") == []
    assert e.corroboration_for("NUMBER_MATCH") == []


def test_console_acts_five_and_six_are_registered():
    from app.api.routes_console import DEMO_ACTS

    assert "act5" in DEMO_ACTS and "act6" in DEMO_ACTS


@pytest.mark.asyncio
async def test_the_demo_covers_every_grade():
    """Guards the stage demo against a policy edit that quietly makes one grade
    unreachable. If this fails, a judge would see an enum with dead values in it."""
    from app.api.routes_console import DEMO_ACTS
    from app.api.routes_reverse import run_reverse

    seen = set()
    for req in DEMO_ACTS.values():
        seen.add((await _investigator().investigate(req)).chain_grade)
    seen.add((await run_reverse("+96279999999", MockProvider())).chain_grade)
    assert seen == set(ChainGrade), f"grades never shown on stage: {set(ChainGrade) - seen}"


def test_a_pre_grading_chain_reads_back_as_ungraded_not_as_a_grade():
    """A chain signed before grading existed must never be served a grade the
    vault did not attest. null is honest; a default would be a quiet lie sitting
    beside a signature that still reports valid."""
    from app.chain.models import Verdict

    legacy = (
        '{"decision":"ALLOW","confidence":0.1,"hypothesis":"legit","reason":"ok",'
        '"chain_id":"chn_legacy","chain":[],"evidence_cost":1.0,"latency_ms":40,'
        '"provider_sources":["mock"]}'
    )
    verdict = Verdict.model_validate_json(legacy)
    assert verdict.chain_grade is None
