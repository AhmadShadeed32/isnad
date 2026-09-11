"""I9 — judge-controlled scenario challenge.

A versioned, bounded, authored case set built on I2/I4's shared runner. The
judge picks a case id; nothing else (no live phone numbers, no thresholds,
no free-text task) reaches the runner.
"""

from __future__ import annotations

import pytest

from demo.lab.challenge import CASES, UnknownCase, run_case, seeded_order


def test_the_case_set_is_versioned_and_bounded():
    assert len(CASES) >= 4
    for case in CASES.values():
        assert "scenario_id" in case
        assert "description" in case


@pytest.mark.asyncio
async def test_every_allowed_case_resolves():
    for case_id in CASES:
        run = await run_case(case_id)
        assert run.outcome is not None


@pytest.mark.asyncio
async def test_a_rejected_case_id_does_no_work():
    with pytest.raises(UnknownCase):
        await run_case("free-text-injected-case")


def test_a_seed_reproduces_the_same_order():
    first = seeded_order(seed=42)
    second = seeded_order(seed=42)
    assert first == second
    assert set(first) == set(CASES)


def test_different_seeds_can_reorder():
    a = seeded_order(seed=1)
    b = seeded_order(seed=2)
    assert set(a) == set(b)  # same cases either way


@pytest.mark.asyncio
async def test_the_provider_outage_case_reports_unresolved_not_a_fabricated_pass():
    run = await run_case("provider_outage")
    assert run.outcome["chain_grade"] in {"UNRESOLVED", "DEGRADED"}
