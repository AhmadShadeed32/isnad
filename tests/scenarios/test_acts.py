"""End-to-end scenario tests — the demo's three acts run the real engine.

These assert the *decision* and that the agent gathered evidence agentically
(cheapest first, escalating only when suspicious).
"""
from __future__ import annotations

import pytest

from app.agent.investigator import build_investigator
from app.domain.enums import Action, Decision
from app.domain.schemas import Money, RequestContext, VerificationRequest
from app.providers.mock import MockProvider


def _investigator():
    return build_investigator(MockProvider())


@pytest.mark.asyncio
async def test_act1_kill_the_otp_allows_silently():
    """Act I — clean signup: one silent Number Verification clears them."""
    req = VerificationRequest(
        phone_number="+962790000001",
        context=RequestContext(event="signup", account_age_days=0),
    )
    verdict = await _investigator().investigate(req)
    assert verdict.decision == Decision.ALLOW
    # Cheapest evidence first: Number Verification is step 1.
    assert verdict.chain[0].action == Action.NUMBER_VERIFY
    # No OTP friction was needed.
    assert all(link.action != Action.STEP_UP_OTP for link in verdict.chain)


@pytest.mark.asyncio
async def test_act2_catch_the_ghost_declines_with_chain():
    """Act II — SIM swapped 41 min ago, new device, wrong location -> DECLINE."""
    req = VerificationRequest(
        phone_number="+962790000002",
        context=RequestContext(
            event="checkout",
            payment_method="cod",
            account_age_days=0,
            amount=Money(value=4200, currency="USD"),
        ),
    )
    verdict = await _investigator().investigate(req)
    assert verdict.decision == Decision.DECLINE
    signals = {link.signal for link in verdict.chain}
    assert "SIM_SWAPPED" in signals
    assert verdict.confidence >= 0.8
    # The verdict is explained, not a black-box score.
    assert "swap" in verdict.reason.lower()


@pytest.mark.asyncio
async def test_act3_approve_the_invisible():
    """Act III — no merchant history, but years of SIM tenure clear them -> ALLOW.

    Starts uncertain (new account + high-value COD) so the agent must actually
    investigate; a stable, long-tenure SIM is what tips it to ALLOW.
    """
    req = VerificationRequest(
        phone_number="+962790000003",
        context=RequestContext(
            event="checkout",
            payment_method="cod",
            account_age_days=0,
            amount=Money(value=1500, currency="USD"),
        ),
    )
    verdict = await _investigator().investigate(req)
    assert verdict.decision == Decision.ALLOW
    # The agent gathered evidence (did not clear on the prior alone) and the
    # SIM-tenure signal is part of the chain.
    assert len(verdict.chain) >= 2
    assert any(link.signal == "SIM_STABLE" for link in verdict.chain)


@pytest.mark.asyncio
async def test_agent_stops_early_and_within_budget():
    """The agent should not run all seven APIs when a verdict is reached cheaply."""
    req = VerificationRequest(
        phone_number="+962790000001",
        context=RequestContext(event="signup", account_age_days=0),
    )
    verdict = await _investigator().investigate(req)
    assert len(verdict.chain) < 7
