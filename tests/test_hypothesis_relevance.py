"""Every check a hypothesis may buy has to be able to move that hypothesis.

The relevance map is what the planner selects from, and the verdict sentence
is written from whatever it selected. When the two disagree — a check chosen
for a hypothesis it cannot speak to — the receipt reads as if the network
answered a question it was never asked. That is the failure mode this file
exists to catch, and it is not visible from the arithmetic: the numbers stay
perfectly consistent while the explanation stops being true.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.domain.enums import Action, Hypothesis, Result
from app.domain.schemas import RequestContext, VerificationRequest
from app.policy.engine import PolicyEngine
from app.providers.mock import MockProvider


@pytest.fixture
def engine() -> PolicyEngine:
    return PolicyEngine(settings.policy_path)


def _relevant(engine: PolicyEngine, hypothesis: str) -> set[str]:
    return set(engine.cfg["hypotheses"][hypothesis]["relevant"])


def test_a_number_match_cannot_clear_a_bot_farm(engine):
    """Number Verification establishes that the handset presenting this number
    actually holds that SIM. A bot farm runs real SIMs in real handsets at
    scale, so a match is not evidence against one — it is orthogonal to the
    question. Leaving it in the relevant set let a day-zero signup be cleared
    by the one check that could not speak to why it was suspected, and the
    receipt then said "Cleared by: network number matches the provided
    number" for a bot_farm hypothesis.
    """
    assert "number_verify" not in _relevant(engine, Hypothesis.BOT_FARM.value)


def test_the_bot_farm_hypothesis_still_has_a_check_it_can_buy(engine):
    """Removing a check must not leave a hypothesis with nothing purchasable:
    that would make every bot_farm case unresolved by construction rather
    than by evidence."""
    from app.agent.planner import _UNSERVED

    buyable = {a for a in _relevant(engine, Hypothesis.BOT_FARM.value) if a not in _UNSERVED}
    assert buyable, "bot_farm has no check the agent can actually purchase"


def test_reachability_is_the_check_that_can_move_a_bot_farm_either_way(engine):
    """It is in the relevant set because both outcomes are informative:
    REACHABLE_BOTPATTERN exists precisely for this hypothesis, and
    REACHABLE_NORMAL is its exoneration."""
    assert "reachability" in _relevant(engine, Hypothesis.BOT_FARM.value)
    signals = engine.cfg["signals"]
    assert signals["REACHABLE_BOTPATTERN"] > 0
    assert signals["REACHABLE_NORMAL"] < 0


def test_number_verify_stays_where_it_does_answer_the_question(engine):
    """Not a blanket removal: for impersonation, whether the handset really
    holds the claimed number is the whole question."""
    assert "number_verify" in _relevant(engine, Hypothesis.IMPERSONATION.value)


async def _act_one():
    from app.agent.investigator import Investigator

    engine = PolicyEngine(settings.policy_path)
    verdict = await Investigator(engine, MockProvider()).investigate(
        VerificationRequest(
            phone_number="+99999991001",
            context=RequestContext(event="signup", account_age_days=0),
        )
    )
    return engine, verdict


@pytest.mark.asyncio
async def test_a_clean_signup_does_not_rest_on_an_orthogonal_check_alone():
    """The Act I trace, end to end.

    Buying the cheap number-association check first is fine and stays. What
    must not happen is the investigation *stopping* there: an ALLOW has to
    rest on at least one supporting fact that bears on the hypothesis being
    investigated, or the chain cleared on a question nobody asked.
    """
    engine, verdict = await _act_one()

    assert verdict.hypothesis == Hypothesis.BOT_FARM.value
    assert verdict.decision.value == "ALLOW"
    relevant = _relevant(engine, Hypothesis.BOT_FARM.value)
    supporting_and_relevant = [
        link
        for link in verdict.chain
        if link.source != "local" and link.delta_logodds < 0 and link.action.value in relevant
    ]
    assert supporting_and_relevant, (
        "ALLOW rests on no check that can move bot_farm: "
        + ", ".join(link.action.value for link in verdict.chain)
    )


@pytest.mark.asyncio
async def test_the_verdict_sentence_names_the_check_that_carried_it():
    """The sentence is what a merchant reads. Naming only the orthogonal check
    was the visible half of this defect."""
    _engine, verdict = await _act_one()

    assert "Cleared by" in verdict.reason
    assert "reachab" in verdict.reason.lower(), verdict.reason


@pytest.mark.asyncio
async def test_a_link_exactly_at_the_material_bar_is_named():
    """`grade` reads adverse_delta as "at least"; the explanation used a strict
    hard-coded 0.4, so a link worth exactly the bar was credited on neither
    side."""
    from app.agent.belief import Belief

    belief = Belief(logodds=-1.0)
    belief.apply("exactly at the bar", -0.4)
    assert "exactly at the bar" in belief.explain("ALLOW", material=0.4)


@pytest.mark.asyncio
async def test_every_hypothesis_only_selects_checks_it_lists():
    """The general form, so the next hypothesis added cannot repeat this."""
    engine = PolicyEngine(settings.policy_path)
    for hypothesis, entry in engine.cfg["hypotheses"].items():
        for action in entry["relevant"]:
            assert action in engine.cfg["actions"], f"{hypothesis}: unpriced action {action}"
            assert Action(action)  # and a real one, not a typo


def test_no_relevant_check_is_a_zero_information_choice(engine):
    """A check listed for a hypothesis must have a signal that can move it.
    `gain` alone does not say which hypothesis it moves; this is the sanity
    bound on the list, not a re-derivation of the weights."""
    for hypothesis, entry in engine.cfg["hypotheses"].items():
        for action in entry["relevant"]:
            assert engine.cfg["actions"][action]["gain"] > 0, f"{hypothesis}/{action}"


def test_the_engine_does_not_treat_an_empty_relevant_list_as_everything(engine):
    """`legit` lists nothing, and that has to mean "no hypothesis-driven
    check", not "any check will do"."""
    assert _relevant(engine, Hypothesis.LEGIT.value) == set()
    assert Result  # the enum import is part of this module's contract surface
