"""Parallel evidence gathering — latency bought with cost.

Opt-in per request. Sequential remains the default and the right default:
cheapest-first-then-stop is what makes the cost story true, and it is why a
clean chain often costs one call instead of six.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.agent.investigator import build_investigator
from app.domain.schemas import Money, RequestContext, VerificationRequest
from app.providers.mock import MockProvider

_REQ = VerificationRequest(
    phone_number="+99999991000",
    context=RequestContext(
        event="checkout",
        payment_method="cod",
        account_age_days=0,
        amount=Money(value=4200),
    ),
)


async def _run(parallel: bool, delay_ms: int = 0):
    return await build_investigator(MockProvider(step_delay_ms=delay_ms)).investigate(
        _REQ, parallel=parallel
    )


@pytest.mark.asyncio
async def test_parallel_is_off_unless_asked():
    """Nothing changes for existing callers. The policy default is sequential."""
    sequential = await _run(parallel=False)
    default = await build_investigator(MockProvider()).investigate(_REQ)
    assert len(default.chain) == len(sequential.chain)


@pytest.mark.asyncio
async def test_a_batch_really_runs_concurrently():
    """The whole point. Three 300ms calls should take about 300ms, not 900ms."""
    started = time.perf_counter()
    verdict = await _run(parallel=True, delay_ms=300)
    elapsed = time.perf_counter() - started

    assert len(verdict.chain) >= 3
    assert elapsed < 0.75, f"batch took {elapsed:.2f}s — it ran sequentially"


@pytest.mark.asyncio
async def test_the_verdict_reports_the_time_the_caller_actually_waited():
    """`latency_ms` used to be the SUM of the link latencies — a number parallel
    mode could not move, so the mode whose entire purpose is latency reported no
    improvement, and the T5 counterfactual published that sum as
    `basis="measured"` next to an OTP round trip measured in seconds.

    Note the link latencies the mock reports are fabricated per action
    (`45 * (1 + index % 3)`) and have nothing to do with `step_delay_ms`, which
    is what made the old number look stable at 315ms in both modes. Wall clock
    is the only measurement here that is real.
    """
    started = time.perf_counter()
    parallel = await _run(parallel=True, delay_ms=250)
    elapsed_ms = (time.perf_counter() - started) * 1000
    sequential = await _run(parallel=False, delay_ms=250)

    assert len(parallel.chain) >= 3
    # It reports its own elapsed time, within scheduling noise.
    assert abs(parallel.latency_ms - elapsed_ms) < 100
    # And that time is genuinely shorter than doing the same work in order.
    assert parallel.latency_ms < sequential.latency_ms


_CLEAN = VerificationRequest(
    phone_number="+99999991001",
    context=RequestContext(event="signup", account_age_days=0),
)


async def _run_req(req, parallel: bool):
    return await build_investigator(MockProvider()).investigate(req, parallel=parallel)


@pytest.mark.asyncio
async def test_parallel_costs_more_on_a_clean_chain():
    """The honest trade, pinned so nobody claims this is free.

    A clean signup clears on the first cheap check, so sequential pays 1 and
    parallel pays 5 — it bought evidence that was never needed. This is exactly
    what weakens the T5 counterfactual, and it is the case to quote if a judge
    asks what parallel costs.
    """
    sequential = await _run_req(_CLEAN, parallel=False)
    parallel = await _run_req(_CLEAN, parallel=True)
    assert sequential.evidence_cost == 1.0 and len(sequential.chain) == 1
    assert parallel.evidence_cost == 5.0 and len(parallel.chain) == 3


@pytest.mark.asyncio
async def test_parallel_is_never_cheaper():
    """On a chain that spends its budget anyway the two are equal — the takeover
    case forces corroboration either way — but parallel must never come out
    below sequential, or the cost story would be backwards.
    """
    for req in (_CLEAN, _REQ):
        sequential = await _run_req(req, parallel=False)
        parallel = await _run_req(req, parallel=True)
        assert parallel.evidence_cost >= sequential.evidence_cost


@pytest.mark.asyncio
async def test_both_modes_reach_the_same_decision():
    """Speed must not change the answer."""
    sequential = await _run(parallel=False)
    parallel = await _run(parallel=True)
    assert parallel.decision == sequential.decision


@pytest.mark.asyncio
async def test_belief_is_applied_in_chain_order_not_completion_order():
    """Two runs over the same evidence must produce the same number regardless
    of which network call happened to answer first."""
    first = await _run(parallel=True)
    second = await _run(parallel=True)
    assert first.confidence == second.confidence
    assert [link.step for link in first.chain] == sorted(link.step for link in first.chain)


@pytest.mark.asyncio
async def test_a_batch_never_overspends_the_budget():
    verdict = await _run(parallel=True)
    engine = build_investigator(MockProvider()).engine
    assert verdict.evidence_cost <= engine.budget_for(_REQ.context)


@pytest.mark.asyncio
async def test_parallel_does_not_break_the_local_evidence_path():
    """Local evidence is applied before the batch; both must land in the chain."""
    from app.api.routes_reverse import run_reverse

    verdict = await run_reverse("+96279999999", MockProvider(), claimed_identity="Demo Bank")
    assert any(link.source == "local" for link in verdict.chain)
    assert any(link.source != "local" for link in verdict.chain)


@pytest.mark.asyncio
async def test_concurrent_runs_do_not_interleave_chains():
    """Two investigations in flight at once must not put each other's links in
    the wrong chain.

    Asserted by giving the two runs DIFFERENT evidence and checking each chain
    carries only its own. The old version compared two freshly generated UUIDs
    and two chain lengths from the same fixture — both true however badly the
    links were mixed, since a swap of one link for another of the same shape
    changes neither.
    """
    from app.domain.enums import Action, Result

    def _scenario(marker: str):
        return {
            action: (Result.PASS, signal, f"detail for {marker}")
            for action, signal in (
                (Action.NUMBER_VERIFY, "NUMBER_MATCH"),
                (Action.SIM_SWAP, "SIM_STABLE"),
                (Action.DEVICE_SWAP, "DEVICE_STABLE"),
                (Action.LOCATION_VERIFY, "AT_CLAIMED_LOCATION"),
                (Action.REACHABILITY, "REACHABLE_NORMAL"),
                (Action.ROAMING, "HOME_NETWORK"),
                (Action.DEVICE_INTELLIGENCE, "DEVICE_TRUSTED"),
            )
        }

    async def _run_marked(marker: str, number: str):
        request = VerificationRequest(
            phone_number=number,
            context=RequestContext(
                event="checkout",
                payment_method="cod",
                account_age_days=0,
                amount=Money(value=4200),
            ),
        )
        provider = MockProvider(scenarios={number: _scenario(marker)})
        return await build_investigator(provider).investigate(request, parallel=True)

    # Interleaved on purpose: both are in flight across every await.
    a, b = await asyncio.gather(_run_marked("A", "+99999991010"), _run_marked("B", "+99999991011"))

    assert a.chain_id != b.chain_id
    assert a.chain and b.chain
    assert all(link.detail == "detail for A" for link in a.chain), [link.detail for link in a.chain]
    assert all(link.detail == "detail for B" for link in b.chain), [link.detail for link in b.chain]
    # And each chain numbers its own steps from 1, with no gaps.
    for verdict in (a, b):
        assert [link.step for link in verdict.chain] == list(range(1, len(verdict.chain) + 1))
