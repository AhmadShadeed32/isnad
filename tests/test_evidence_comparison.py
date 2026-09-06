"""I3 — the combined evidence/decision comparison report.

Loaded from the script file directly (same pattern as
test_false_decline_baseline.py) so it exercises the real aggregator.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "build_evidence_comparison", Path(__file__).resolve().parents[1] / "scripts" / "build_evidence_comparison.py"
)
comparison_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(comparison_script)


@pytest.mark.asyncio
async def test_the_report_carries_both_sources_and_named_denominators():
    report = await comparison_script.build_report()
    assert report["independent_evaluation"]["case_count"] > 0
    assert report["false_decline_baseline"]["case_count"] > 0
    assert report["false_decline_baseline"]["innocent_denominator"] > 0
    assert report["false_decline_baseline"]["guilty_denominator"] > 0
    assert report["policy_digest"]
    assert report["limits"], "every claim needs its own stated limitation"


@pytest.mark.asyncio
async def test_false_declines_are_counted_only_among_the_innocent_denominator():
    report = await comparison_script.build_report()
    fd = report["false_decline_baseline"]["false_declines"]
    innocent = report["false_decline_baseline"]["innocent_denominator"]
    for count in fd.values():
        assert 0 <= count <= innocent


@pytest.mark.asyncio
async def test_the_report_is_reproducible_across_two_runs():
    first = await comparison_script.build_report()
    second = await comparison_script.build_report()
    assert first["independent_evaluation"]["methods"] == second["independent_evaluation"]["methods"]
    assert first["false_decline_baseline"] == second["false_decline_baseline"]
    assert first["policy_digest"] == second["policy_digest"]
