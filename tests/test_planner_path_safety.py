"""The decision boundary, held across every path the planner can take.

The rule this file exists to enforce, in one sentence: **a SIM-change signal
alone must not carry an automatic DECLINE while the checks policy requires to
confirm or clear it are missing, unavailable or unaffordable.** The answer in
that case is CHALLENGE, with the unresolved reason named.

Everything here is deterministic. Planner order is scripted, provider answers
come from explicit fixtures, and no test depends on a demo act, a demo phone
number, a scenario label or a run id — the boundary is a property of the
policy and the investigator, and a test that identified the case by its name
would prove nothing about a real request.

What this file does NOT establish: fraud accuracy. Nothing here is measured
against outcomes. It shows that the agent's stated policy is the policy it
actually executes.
"""

from __future__ import annotations

import asyncio
import copy

import pytest
import yaml

from app.agent.investigator import Investigator
from app.agent.planner import Choice, GreedyPlanner
from app.domain.enums import Action, ChainGrade, Decision, Hypothesis, Result
from app.domain.schemas import Area, Money, RequestContext, VerificationRequest
from app.policy.engine import PolicyEngine
from app.providers.mock import MockProvider

# A number with no scripted scenario anywhere in the codebase. Every fixture
# below is passed in explicitly, so nothing here can accidentally exercise a
# demo act.
SUBJECT = "+99999997777"
CLAIM = Area(lat=31.9539, lon=35.9106, radius_m=2000)

A = Action


# --- fixtures: what the network says -----------------------------------------
#
# Told apart only by WHICH checks answer and how, never by prose or by number.

#: A genuine SIM replacement: the handset stayed, and the device is where the
#: customer says it is. The corroboration policy asks for exists and answers.
REPLACEMENT = {
    A.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH"),
    A.SIM_SWAP: (Result.FLAG, "SIM_SWAPPED"),
    A.DEVICE_SWAP: (Result.PASS, "DEVICE_STABLE"),
    A.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION"),
    A.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL"),
    A.ROAMING: (Result.PASS, "HOME_NETWORK"),
    A.NUMBER_RECYCLING: (Result.PASS, "NUMBER_CONTINUOUS"),
}

#: The same SIM change, with both corroborating checks unable to answer. This
#: is the shape that used to DECLINE on one signal.
UNCORROBORATED = {
    **REPLACEMENT,
    A.DEVICE_SWAP: (Result.INFO, "EVIDENCE_UNAVAILABLE"),
    A.LOCATION_VERIFY: (Result.INFO, "LOCATION_UNKNOWN"),
}

#: A SIM change the network cannot corroborate, sitting beside a SECOND
#: adverse finding that policy does not gate. The gated signal is unconfirmed;
#: the number mismatch is not, and the decline stands on that one.
MIXED_ADVERSE = {
    **UNCORROBORATED,
    A.NUMBER_VERIFY: (Result.FLAG, "NUMBER_MISMATCH"),
}

#: A takeover: the SIM changed AND the handset changed. The device swap is
#: independent adverse evidence that policy does not gate, so a decline may
#: stand on it.
TAKEOVER = {
    **REPLACEMENT,
    A.DEVICE_SWAP: (Result.FLAG, "DEVICE_SWAPPED"),
    A.LOCATION_VERIFY: (Result.FLAG, "NOT_AT_CLAIMED_LOCATION"),
}

#: Nothing adverse anywhere.
CLEAN = {**REPLACEMENT, A.SIM_SWAP: (Result.PASS, "SIM_STABLE")}


def context(*, amount: float = 1500, claim: Area | None = CLAIM) -> RequestContext:
    """A high-value cash-on-delivery checkout from a day-old account: the prior
    a SIM change pushes over the decline line. `claim` is the merchant's own
    location claim, and its absence is a real condition, not an omission."""
    return RequestContext(
        event="checkout",
        payment_method="cod",
        account_age_days=0,
        amount=Money(value=amount),
        claimed_location=claim,
    )


# --- planners ----------------------------------------------------------------


class ScriptedPlanner:
    """A fixed selection order, then stop.

    `source` is `"llm"` because these tests exercise the model-planner code
    path — but nothing in this file asserts that a Gemini call happened, and
    no evidence produced here is presented as a real model run.
    """

    source = "llm"

    def __init__(self, engine: PolicyEngine, order, stop_after: int | None = None):
        self.engine = engine
        self.order = list(order)
        self.index = 0
        self.stop_after = stop_after
        self._greedy = GreedyPlanner(engine)

    def choose(self, hypothesis, used, budget_left, p_fraud=0.0, observations=()):
        if self.stop_after is not None and len(used) >= self.stop_after:
            return Choice(None, "scripted: stop", self.source)
        while self.index < len(self.order):
            action = self.order[self.index]
            self.index += 1
            if action not in used and self.engine.action_cost(action) <= budget_left:
                return Choice(action, "scripted: fixed order", self.source)
        return Choice(None, "scripted: order exhausted", self.source)

    def next_best(self, hypothesis, used, budget_left):
        return self.choose(hypothesis, used, budget_left).action

    def cheapest_stepup(self, used, budget_left):
        return self._greedy.cheapest_stepup(used, budget_left)


class RefusingPlanner:
    """Every ask stops selection without selecting. This is the shape of
    invalid output, a rejected response and the model-call ceiling: something
    answered, so greedy must never quietly substitute for it."""

    source = "llm"

    def __init__(self, engine: PolicyEngine, rationale: str):
        self.engine = engine
        self.rationale = rationale
        self.asked = 0
        self._greedy = GreedyPlanner(engine)

    def choose(self, hypothesis, used, budget_left, p_fraud=0.0, observations=()):
        self.asked += 1
        return Choice(None, self.rationale, self.source)

    def next_best(self, hypothesis, used, budget_left):
        return None

    def cheapest_stepup(self, used, budget_left):
        return self._greedy.cheapest_stepup(used, budget_left)


# --- harness -----------------------------------------------------------------


def engine_with(tmp_path, **overrides) -> PolicyEngine:
    """A private policy engine, so a budget experiment cannot leak into the
    cached engine every other test shares."""
    from app.config import settings

    with open(settings.policy_path) as handle:
        cfg = copy.deepcopy(yaml.safe_load(handle))
    for dotted, value in overrides.items():
        node = cfg
        *path, leaf = dotted.split(".")
        for part in path:
            node = node[part]
        node[leaf] = value
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return PolicyEngine(path)


def investigate(
    scenario,
    *,
    engine: PolicyEngine | None = None,
    order=None,
    planner=None,
    ctx: RequestContext | None = None,
    parallel: bool | None = None,
    provider=None,
):
    """One complete investigation, with everything that varies made explicit."""
    from app.config import settings

    engine = engine or PolicyEngine(settings.policy_path)
    provider = provider or MockProvider(scenarios={SUBJECT: scenario})
    chosen = planner or ScriptedPlanner(engine, order or [])
    events: list[dict] = []

    async def sink(event):
        events.append(dict(event))

    agent = Investigator(engine, provider, planner=chosen, event_sink=sink)
    request = VerificationRequest(phone_number=SUBJECT, context=ctx or context())
    verdict = asyncio.run(agent.investigate(request, parallel=parallel))
    return verdict, events


def signals(verdict):
    return [link.signal for link in verdict.chain]


def actions(verdict):
    return [link.action for link in verdict.chain]


# --- 1. the boundary, across path variations ---------------------------------


ORDERS = {
    "sim_first": [A.SIM_SWAP, A.DEVICE_SWAP, A.LOCATION_VERIFY],
    "verification_first": [A.NUMBER_VERIFY, A.SIM_SWAP, A.DEVICE_SWAP],
    "costly_checks_first": [A.LOCATION_VERIFY, A.ROAMING, A.REACHABILITY, A.SIM_SWAP],
    "sim_then_everything": [A.SIM_SWAP, A.ROAMING, A.REACHABILITY, A.NUMBER_VERIFY],
}


@pytest.mark.parametrize("name", sorted(ORDERS))
def test_a_replacement_sim_never_declines_whatever_order_the_checks_come_in(name):
    verdict, _ = investigate(REPLACEMENT, order=ORDERS[name])
    assert verdict.decision != Decision.DECLINE, name


@pytest.mark.parametrize("name", sorted(ORDERS))
def test_an_uncorroborated_sim_change_never_declines_whatever_the_order(name):
    verdict, _ = investigate(UNCORROBORATED, order=ORDERS[name])
    assert verdict.decision != Decision.DECLINE, name


def test_a_sim_change_alone_with_no_corroboration_challenges_rather_than_declines():
    """The regression this whole step exists for.

    Before the gate, this path produced DECLINE at a raw score of 0.876 with a
    chain that had never established anything: the SIM check flagged, and both
    checks policy names as able to clear it came back "we could not check".
    """
    verdict, _ = investigate(UNCORROBORATED, order=[A.SIM_SWAP, A.DEVICE_SWAP])

    assert verdict.decision == Decision.CHALLENGE
    assert "SIM_SWAPPED" in signals(verdict)
    # The raw score is preserved exactly as measured. The gate changes what is
    # DONE about the number, never the number.
    assert verdict.confidence >= verdict.policy_snapshot["decline_above"]


def test_an_early_stop_right_after_the_sim_check_is_still_gated():
    """STOP is a first-class planner outcome and used to leave the loop before
    the corroboration branch could run."""
    verdict, _ = investigate(UNCORROBORATED, order=[A.SIM_SWAP], planner=None)
    assert verdict.decision == Decision.CHALLENGE
    assert verdict.stopping_reason


def test_the_parallel_gather_path_is_gated_too():
    verdict, _ = investigate(UNCORROBORATED, order=[A.SIM_SWAP], parallel=True)
    assert verdict.decision != Decision.DECLINE


def test_a_budget_exhausted_before_the_gate_is_still_gated(tmp_path):
    """The gate used to live inside `while budget_left > 0`, so a run that
    spent its last unit on the SIM check never reached it."""
    engine = engine_with(tmp_path, **{"budget.high_value": 3})
    verdict, _ = investigate(UNCORROBORATED, engine=engine, order=[A.SIM_SWAP])
    assert verdict.stopping_reason in {"budget_exhausted", "nothing_affordable", "decisive"}
    assert verdict.decision != Decision.DECLINE


# --- 2. what the gate says about itself --------------------------------------


def test_the_unmet_check_its_reason_and_the_budget_are_all_inspectable():
    verdict, _ = investigate(UNCORROBORATED, order=[A.SIM_SWAP, A.DEVICE_SWAP])

    (gap,) = verdict.unmet_corroboration
    assert gap.signal == "SIM_SWAPPED"
    assert gap.required == ["device_swap", "location_verify"]
    assert gap.resolved == []
    assert gap.reason == "unresolved"
    assert verdict.budget_remaining >= 0
    assert verdict.operations >= len(verdict.chain)
    assert verdict.stopping_reason


def test_an_uncorroborated_challenge_is_not_explained_as_a_refuted_chain():
    """REFUTED means "a link directly contradicts the claim". Nothing in this
    chain established the SIM finding, so that grade would be a claim the links
    do not make — while the score that produced it stays exactly as measured."""
    verdict, _ = investigate(UNCORROBORATED, order=[A.SIM_SWAP, A.DEVICE_SWAP])
    assert verdict.chain_grade != ChainGrade.REFUTED


def test_the_reason_sentence_says_the_finding_was_not_confirmed():
    verdict, _ = investigate(UNCORROBORATED, order=[A.SIM_SWAP, A.DEVICE_SWAP])
    assert "not corroborated" in verdict.reason
    assert "SIM_SWAPPED" in verdict.reason


def test_the_merchant_facing_summary_says_it_too():
    from app.presentation import present

    verdict, _ = investigate(UNCORROBORATED, order=[A.SIM_SWAP, A.DEVICE_SWAP])
    view = present(verdict)

    assert view.title == "Additional verification needed"
    assert view.unmet_corroboration
    assert "not corroborated" in view.summary
    # And it must NOT tell the merchant the agent finished and was merely
    # unsure: that is a different run from this one.
    assert "simply landed in a range" not in view.summary


def test_the_gate_reaches_the_live_event_stream():
    _, events = investigate(UNCORROBORATED, order=[A.SIM_SWAP, A.DEVICE_SWAP])
    (verdict_event,) = [event for event in events if event["type"] == "verdict"]
    assert verdict_event["uncorroborated"] == ["SIM_SWAPPED"]
    assert verdict_event["stopping_reason"]
    assert "operations" in verdict_event and "budget_remaining" in verdict_event


# --- 3. controls: what must still decline, and still allow -------------------


def test_independent_adverse_evidence_still_declines():
    """A device swap is not gated by policy, so a chain carrying one is not
    resting on the SIM change alone and the decline stands."""
    verdict, _ = investigate(TAKEOVER, order=[A.SIM_SWAP, A.DEVICE_SWAP])
    assert verdict.decision == Decision.DECLINE
    assert "DEVICE_SWAPPED" in signals(verdict)


def test_a_corroborating_check_that_comes_back_adverse_satisfies_the_requirement():
    """Corroboration means "the check answered", not "the check agreed". A
    device swap that answers FLAG is exactly the confirmation the gate was
    waiting for, and it confirms the decline rather than blocking it."""
    verdict, _ = investigate(TAKEOVER, order=[A.SIM_SWAP, A.DEVICE_SWAP])
    assert verdict.unmet_corroboration == []
    assert verdict.decision == Decision.DECLINE


def test_a_resolved_clearing_check_also_satisfies_the_requirement():
    verdict, _ = investigate(REPLACEMENT, order=[A.SIM_SWAP, A.DEVICE_SWAP])
    assert verdict.unmet_corroboration == []
    assert verdict.decision != Decision.DECLINE


def test_a_decline_stands_when_an_UNGATED_adverse_finding_sits_beside_the_gated_one():
    """The carve-out, and the narrowest part of the whole rule.

    The SIM change here is exactly as uncorroborated as in the regression case
    above — the gate reports it as unmet — but the chain also carries a number
    mismatch, which policy names no corroboration for. The customer is not
    being declined on an unconfirmed signal; they are being declined on the
    confirmed one. Downgrading here would be the opposite failure: refusing to
    act on evidence the agent actually obtained.
    """
    verdict, _ = investigate(
        MIXED_ADVERSE, order=[A.NUMBER_VERIFY, A.SIM_SWAP, A.DEVICE_SWAP]
    )

    assert "NUMBER_MISMATCH" in signals(verdict)
    # The gap is still reported: the SIM finding really was never corroborated,
    # and hiding that because the decision went the other way would make the
    # receipt say less than the run knew.
    assert [gap.signal for gap in verdict.unmet_corroboration] == ["SIM_SWAPPED"]
    assert verdict.decision == Decision.DECLINE


def test_a_clean_checkout_still_allows():
    verdict, _ = investigate(CLEAN, order=[A.NUMBER_VERIFY, A.SIM_SWAP])
    assert verdict.decision == Decision.ALLOW
    assert verdict.unmet_corroboration == []


def test_the_gate_does_not_turn_every_case_into_a_challenge():
    """Guard against the lazy fix. Three fixtures, three different decisions."""
    outcomes = {
        investigate(CLEAN, order=[A.NUMBER_VERIFY, A.SIM_SWAP])[0].decision,
        investigate(UNCORROBORATED, order=[A.SIM_SWAP, A.DEVICE_SWAP])[0].decision,
        investigate(TAKEOVER, order=[A.SIM_SWAP, A.DEVICE_SWAP])[0].decision,
    }
    assert outcomes == {Decision.ALLOW, Decision.CHALLENGE, Decision.DECLINE}


# --- 4. budgets --------------------------------------------------------------


def test_a_budget_below_the_first_check_buys_nothing(tmp_path):
    engine = engine_with(tmp_path, **{"budget.high_value": 0})
    verdict, _ = investigate(UNCORROBORATED, engine=engine, order=[A.SIM_SWAP])
    assert verdict.chain == []
    assert verdict.evidence_cost == 0
    assert verdict.decision != Decision.DECLINE


def test_a_budget_that_covers_the_corroboration_reports_no_gap(tmp_path):
    engine = engine_with(tmp_path, **{"budget.high_value": 12})
    verdict, _ = investigate(REPLACEMENT, engine=engine, order=[A.SIM_SWAP, A.DEVICE_SWAP])
    assert verdict.unmet_corroboration == []


def test_a_budget_just_below_the_corroboration_names_the_budget_as_the_reason(tmp_path):
    """Enough for the SIM check, not enough for anything that could clear it."""
    engine = engine_with(tmp_path, **{"budget.high_value": 2, "enrichments.swap_date.enabled": False})
    verdict, _ = investigate(REPLACEMENT, engine=engine, order=[A.SIM_SWAP])

    assert signals(verdict) == ["SIM_SWAPPED"]
    assert verdict.decision != Decision.DECLINE
    (gap,) = verdict.unmet_corroboration
    assert gap.reason == "budget"
    assert gap.resolved == []


# --- 5. preconditions: a claim the merchant never made -----------------------


def test_no_location_claim_means_no_location_provider_call():
    """Both providers already refuse to call the network with no claim to
    answer. The investigator used to select it anyway and charge full price for
    a link that could only say EVIDENCE_UNAVAILABLE."""
    verdict, _ = investigate(
        REPLACEMENT,
        order=[A.LOCATION_VERIFY, A.SIM_SWAP, A.DEVICE_SWAP],
        ctx=context(claim=None),
    )
    assert A.LOCATION_VERIFY not in actions(verdict)


def test_a_missing_location_claim_is_reported_as_unavailable_not_as_a_budget_problem(
    tmp_path,
):
    engine = engine_with(tmp_path, corroboration={"SIM_SWAPPED": ["location_verify"]})
    verdict, _ = investigate(
        REPLACEMENT, engine=engine, order=[A.SIM_SWAP], ctx=context(claim=None)
    )
    (gap,) = verdict.unmet_corroboration
    assert gap.reason == "unavailable"
    assert verdict.decision != Decision.DECLINE


# --- 6. enrichment must not starve the decision ------------------------------


def test_a_date_call_never_takes_the_budget_a_required_check_needs(tmp_path):
    """The date explains a link; the corroborating check decides the case.

    With room for the SIM check plus exactly one more operation, the corroborating
    check is what gets bought.
    """
    engine = engine_with(tmp_path, **{"budget.high_value": 4})
    verdict, _ = investigate(REPLACEMENT, engine=engine, order=[A.SIM_SWAP, A.DEVICE_SWAP])

    assert A.DEVICE_SWAP in actions(verdict)
    assert verdict.unmet_corroboration == []


def test_a_deferred_date_is_settled_when_the_budget_survives_the_check(tmp_path):
    """Deferral, not silent loss: if the required check leaves room, the date
    is asked for after it."""
    engine = engine_with(tmp_path, **{"budget.high_value": 5})
    verdict, _ = investigate(REPLACEMENT, engine=engine, order=[A.SIM_SWAP, A.DEVICE_SWAP])

    (swap,) = [link for link in verdict.chain if link.action == A.SIM_SWAP]
    assert swap.timing is not None
    assert swap.timing.availability != "not_attempted"


def test_every_attempted_date_call_is_counted_even_when_it_fails():
    """`operations` counts what the operator was ASKED, not what it answered."""

    class FailingDates(MockProvider):
        async def enrich_timing(self, action, request, signal):
            raise RuntimeError("operator refused")

    verdict, _ = investigate(
        REPLACEMENT,
        order=[A.SIM_SWAP, A.DEVICE_SWAP],
        provider=FailingDates(scenarios={SUBJECT: REPLACEMENT}),
    )
    dated = [link for link in verdict.chain if link.timing is not None]
    assert dated
    assert all(link.timing.availability == "invalid" for link in dated)
    assert verdict.operations == len(verdict.chain) + len(dated)


def test_an_unsupported_date_operation_stays_free():
    """No request left the process, so nothing is charged and nothing counted —
    the existing zero-spend treatment, unchanged."""

    class NoDates(MockProvider):
        enrich_timing = None

    verdict, _ = investigate(
        REPLACEMENT,
        order=[A.SIM_SWAP, A.DEVICE_SWAP],
        provider=NoDates(scenarios={SUBJECT: REPLACEMENT}),
    )
    from app.config import settings

    engine = PolicyEngine(settings.policy_path)
    assert verdict.operations == len(verdict.chain)
    assert verdict.evidence_cost == sum(
        engine.action_cost(link.action) for link in verdict.chain
    )


def test_a_date_never_changes_the_boolean_risk_signal():
    verdict, _ = investigate(REPLACEMENT, order=[A.SIM_SWAP, A.DEVICE_SWAP])
    (swap,) = [link for link in verdict.chain if link.action == A.SIM_SWAP]
    assert swap.signal == "SIM_SWAPPED"
    assert swap.result == Result.FLAG


# --- 7. the model path -------------------------------------------------------


@pytest.mark.parametrize(
    "rationale",
    [
        "Gemini selection stopped: response rejected or invalid",
        "Gemini selection stopped: model call limit reached",
        "Gemini selection stopped: action is not available",
    ],
)
def test_a_stopped_model_selection_never_becomes_hidden_greedy_selection(rationale):
    """An answer that was rejected is not the same as no answer at all. Greedy
    must not quietly substitute, and the run must still be gated."""
    from app.config import settings

    engine = PolicyEngine(settings.policy_path)
    planner = RefusingPlanner(engine, rationale)
    verdict, events = investigate(UNCORROBORATED, engine=engine, planner=planner)

    assert "greedy" not in verdict.planner
    assert verdict.decision != Decision.DECLINE
    selections = [event for event in events if event["type"] == "decision"]
    assert all(event["planner"] in {"llm", "policy"} for event in selections)


def test_a_policy_choreographed_check_is_never_labelled_a_model_choice():
    """A scripted test planner must not turn a policy step into a claimed
    Gemini selection, and vice versa."""
    _, events = investigate(UNCORROBORATED, order=[A.SIM_SWAP, A.DEVICE_SWAP])
    for event in events:
        if event.get("type") == "decision" and event.get("phase") in {
            "corroboration",
            "attestation",
            "step_up",
            "parallel",
            "continuity",
            "authorization",
        }:
            assert event["planner"] == "policy"


def test_the_gate_holds_under_the_greedy_planner_too():
    from app.config import settings

    engine = PolicyEngine(settings.policy_path)
    verdict, _ = investigate(UNCORROBORATED, engine=engine, planner=GreedyPlanner(engine))
    assert verdict.decision != Decision.DECLINE


# --- 8. no special cases -----------------------------------------------------


@pytest.mark.parametrize("number", ["+99999990001", "+441632960999", "+96279123456"])
def test_the_boundary_does_not_depend_on_which_number_asked(number):
    provider = MockProvider(scenarios={number: UNCORROBORATED})
    from app.config import settings

    engine = PolicyEngine(settings.policy_path)
    agent = Investigator(
        engine, provider, planner=ScriptedPlanner(engine, [A.SIM_SWAP, A.DEVICE_SWAP])
    )
    verdict = asyncio.run(
        agent.investigate(VerificationRequest(phone_number=number, context=context()))
    )
    assert verdict.decision == Decision.CHALLENGE
    assert [gap.signal for gap in verdict.unmet_corroboration] == ["SIM_SWAPPED"]


def test_the_hypothesis_is_formed_from_context_not_from_the_fixture():
    verdict, _ = investigate(UNCORROBORATED, order=[A.SIM_SWAP])
    assert verdict.hypothesis == Hypothesis.ACCOUNT_TAKEOVER.value


# --- 9. receipts -------------------------------------------------------------


def test_a_verdict_carrying_no_gate_fields_still_parses_and_verifies():
    """Every field the gate added is optional and defaulted, so a payload
    signed before it existed reads back unchanged rather than raising."""
    from app.chain.models import Verdict

    legacy = Verdict.model_validate_json(
        '{"decision":"CHALLENGE","confidence":0.5,"hypothesis":"account_takeover",'
        '"reason":"historic","chain_id":"chn_legacy","chain":[]}'
    )
    assert legacy.unmet_corroboration == []
    assert legacy.stopping_reason == ""
    assert legacy.operations == 0


def test_the_gate_fields_travel_inside_the_signature():
    """Not a note beside the verdict: a dispute team reading the receipt later
    has to see why this was a challenge and not a refusal."""
    from app.chain.vault import vault

    verdict, _ = investigate(UNCORROBORATED, order=[A.SIM_SWAP, A.DEVICE_SWAP])
    payload = verdict.model_dump_json()
    signature = vault.sign(payload.encode())

    assert "unmet_corroboration" in payload
    assert vault.verify(payload.encode(), signature)
    tampered = payload.replace('"reason":"unresolved"', '"reason":"budget"')
    if tampered != payload:
        assert not vault.verify(tampered.encode(), signature)
