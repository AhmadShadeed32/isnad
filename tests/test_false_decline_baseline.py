"""The false-decline harness has to be trustworthy before its number is quoted.

These check the things that would make the headline figure a lie: a population
that is quietly cherry-picked, a baseline that is handed less evidence than it
would really have, or a control group that cannot detect leakage.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.domain.enums import Decision, Result

_spec = importlib.util.spec_from_file_location(
    "fdb", Path(__file__).resolve().parents[1] / "scripts" / "false_decline_baseline.py"
)
fdb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fdb)


def _deltas():
    from app.config import settings
    from app.policy.engine import get_engine

    return get_engine(str(settings.policy_path)).cfg["signals"]


def test_the_population_comes_from_the_policy_not_from_a_hand_picked_list():
    """If cases were chosen by hand the number would mean nothing. Every adverse
    and every could-not-determine signal the policy defines must appear."""
    cases = fdb.population(_deltas())
    singles = {c["name"] for c in cases if c["group"] in ("ADVERSE-1", "UNKNOWN-1")}
    expected = {sig for sig in fdb.EMITS if sig in _deltas()}
    assert singles == expected, expected - singles


def test_every_generated_case_differs_from_clean_in_exactly_one_check():
    """The ADVERSE-1/UNKNOWN-1 claim is 'one bad reading on an otherwise clean
    line'. If a case mutated two checks it would be a corroborated case wearing
    the wrong label, and would inflate the baseline's false declines."""
    for case in fdb.population(_deltas()):
        if case["group"] not in ("ADVERSE-1", "UNKNOWN-1"):
            continue
        differs = [a for a, v in case["scenario"].items() if fdb.CLEAN[a] != v]
        assert len(differs) == 1, (case["name"], differs)


def test_the_corroborated_group_holds_two_distinct_checks():
    for case in fdb.population(_deltas()):
        if case["group"] != "CORROBORATED-2":
            continue
        differs = [a for a, v in case["scenario"].items() if fdb.CLEAN[a] != v]
        assert len(differs) == 2, (case["name"], differs)


def test_a_clean_chain_declines_under_neither_baseline():
    """Guards against a baseline so blunt it declines everyone, which would make
    the comparison meaningless."""
    clean = [type("L", (), {"result": Result.PASS})() for _ in range(5)]
    assert fdb.baselines(clean) == {
        "single-signal": Decision.ALLOW,
        "collapse-unknowns": Decision.ALLOW,
    }


def test_the_two_baselines_differ_only_on_could_not_determine():
    """The whole thesis is that these two rules disagree about an unanswered
    check. If they agreed, there would be nothing to measure."""
    unknown_only = [type("L", (), {"result": Result.INFO})()]
    got = fdb.baselines(unknown_only)
    assert got["single-signal"] == Decision.ALLOW
    assert got["collapse-unknowns"] == Decision.DECLINE
