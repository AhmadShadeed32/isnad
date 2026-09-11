"""Low priors and exhausted budgets cannot substitute for supporting evidence."""

import pytest

from app.agent.investigator import Investigator
from app.agent.planner import Choice
from app.config import settings
from app.domain.enums import Action, Decision, Result
from app.domain.schemas import VerificationRequest
from app.policy.engine import PolicyEngine
from app.providers.mock import MockProvider


class StopsImmediately:
    def choose(self, *args, **kwargs):
        return Choice(None, "stop", "llm")

    def cheapest_stepup(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize("budget", [0, 0.5, 8])
async def test_low_prior_allow_requires_a_supporting_fact_even_with_stop(budget):
    engine = PolicyEngine(settings.policy_path)
    engine.cfg["budget"]["default"] = budget
    provider = MockProvider(scenarios={
        "+99999991901": {Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH")}
    })
    investigator = Investigator(engine, provider)
    investigator.planner = StopsImmediately()
    verdict = await investigator.investigate(VerificationRequest(
        phone_number="+99999991901", context={"event": "signup", "account_age_days": 100}
    ))

    assert verdict.evidence_cost <= budget
    if budget < engine.action_cost(Action.NUMBER_VERIFY):
        assert verdict.decision == Decision.CHALLENGE
        assert not verdict.chain
    else:
        assert verdict.decision == Decision.ALLOW
        assert verdict.chain[0].action == Action.NUMBER_VERIFY
        assert verdict.chain[0].delta_logodds < 0
        assert verdict.planner == "policy"
