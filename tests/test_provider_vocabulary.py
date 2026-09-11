"""A fixture may only say what a CAMARA API can return.

This is the test that would have caught "swap detected 41 min ago" — a sentence
that survived five sessions, three documents and a rendered video before anyone
asked how a boolean-against-a-window could produce a timestamp. On stage that is
one question from an operator judge and the demo is over.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from app.domain.enums import Action, Result
from app.providers.mock import _CLEAN, SCENARIOS
from app.providers.vocabulary import SPEAKABLE_SIGNALS, UNBACKED_SIGNALS, detail_for

CAPTURES = pathlib.Path(__file__).resolve().parents[1] / "docs" / "nac"


@pytest.mark.parametrize("number", sorted(SCENARIOS))
def test_every_fixture_signal_is_one_a_network_can_return(number: str) -> None:
    for action, (result, signal) in SCENARIOS[number].items():
        assert isinstance(result, Result)
        assert signal in SPEAKABLE_SIGNALS, f"{number}/{action.value} invents {signal}"
        assert signal not in UNBACKED_SIGNALS, f"{number}/{action.value} claims {signal}"


def test_clean_scenario_is_speakable() -> None:
    for _result, signal in _CLEAN.values():
        assert signal in SPEAKABLE_SIGNALS


def test_device_intelligence_is_never_a_verdict() -> None:
    """No Nokia adapter exists, so no scenario may return a reputation."""
    for number, scenario in SCENARIOS.items():
        entry = scenario.get(Action.DEVICE_INTELLIGENCE)
        if entry is None:
            continue
        result, signal = entry
        assert (result, signal) == (Result.INFO, "EVIDENCE_UNAVAILABLE"), number


def test_swap_details_carry_the_window_not_a_timestamp() -> None:
    """CAMARA answers a boolean against max_age. It cannot date the swap."""
    for signal in ("SIM_SWAPPED", "SIM_STABLE", "DEVICE_SWAPPED", "DEVICE_STABLE"):
        detail = detail_for(signal)
        assert "in the last" in detail or "inside the last" in detail
        assert " ago" not in detail
        assert "h" in detail.split()[-1]


def test_no_fixture_sentence_claims_tenure_or_a_timestamp() -> None:
    banned = ("ago", "years", "first seen", "mid-session", "home cell", "prior fraud")
    for number, scenario in SCENARIOS.items():
        for _result, signal in scenario.values():
            detail = detail_for(signal, connectivity="SMS").lower()
            for phrase in banned:
                assert phrase not in detail, f"{number}: {detail!r} claims {phrase!r}"


def test_signals_match_the_captured_nac_responses() -> None:
    """The signal vocabulary is the one the real captures came back with."""
    for capture in CAPTURES.glob("*.json"):
        signal = json.loads(capture.read_text())["normalized"]["signal"]
        assert signal in SPEAKABLE_SIGNALS, f"{capture.name} returned {signal}"
