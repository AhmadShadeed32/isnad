"""I2 — one-fact counterfactual explorer.

The only supported variant is removing the customer's claimed location: it is
the one input the investigator branches on directly (P1's zero-SDK-call
missing-claim guarantee) while every network signal stays fixed, since the
variant reuses the exact same scripted phone number as the base run.
"""

from __future__ import annotations

import pytest

from demo.lab.compare import NoClaimedLocation, compare_missing_location_claim


@pytest.mark.asyncio
async def test_removing_the_claim_isolates_exactly_one_changed_field():
    comparison = await compare_missing_location_claim("replacement")
    assert comparison.changed_field == "context.claimed_location"
    assert comparison.before_value == "present"
    assert comparison.after_value is None
    assert comparison.base_run_id != comparison.variant_run_id


@pytest.mark.asyncio
async def test_a_scenario_with_no_claim_to_remove_is_rejected():
    with pytest.raises(NoClaimedLocation):
        await compare_missing_location_claim("clean")


@pytest.mark.asyncio
async def test_the_comparison_reports_whether_anything_changed():
    comparison = await compare_missing_location_claim("replacement")
    assert comparison.effect in {"changed", "no_observed_effect"}
    if comparison.effect == "no_observed_effect":
        assert comparison.base_outcome == comparison.variant_outcome
    else:
        assert comparison.base_outcome != comparison.variant_outcome


@pytest.mark.asyncio
async def test_the_original_scenario_run_is_never_mutated_by_comparing_it():
    from demo.lab.runner import run_scenario

    before = await run_scenario("replacement")
    await compare_missing_location_claim("replacement")
    after = await run_scenario("replacement")
    assert before.outcome == after.outcome
    assert before.fixture_digest == after.fixture_digest


@pytest.mark.asyncio
async def test_concurrent_comparisons_do_not_share_state():
    import asyncio

    first, second = await asyncio.gather(
        compare_missing_location_claim("replacement"), compare_missing_location_claim("replacement")
    )
    assert first.base_run_id != second.base_run_id
    assert first.variant_run_id != second.variant_run_id
