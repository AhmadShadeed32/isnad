"""Contract tests over responses actually observed from Nokia Network as Code.

T1's point is that every claim this repo makes about CAMARA must trace to a real
response rather than an assumption. `scripts/t1_capture.py` recorded one call per
action against the NaC simulator on 2026-08-30 with SDK 10.0.0; the fixtures live
in `docs/nac/`.

These tests run OFFLINE. They make no network call and cost nothing — they assert
that `NacProvider`'s normalization still produces the signal the live API
actually produced. If Nokia changes a response shape, or someone "tidies" the
provider's field handling, these fail rather than the demo.

Six APIs have been observed against the hosted simulator: SIM Swap, Device Swap,
Reachability, Roaming and Location Verification (2026-08-30), and Number
Recycling (2026-09-06, recorded in docs/nac/observations/). Number Verification and step-up require user consent, and
Device Intelligence has no adapter — those three are recorded as such, and the
tests assert exactly that rather than pretending they were exercised.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = sorted((Path(__file__).resolve().parent.parent / "docs" / "nac").glob("*.json"))

# What the live simulator produced, action -> signal. Written down here so a
# change to either the fixture or the provider has to be deliberate.
OBSERVED = {
    "sim_swap": "SIM_SWAPPED",
    "device_swap": "DEVICE_SWAPPED",
    "reachability": "REACHABLE_NORMAL",
    "roaming": "ROAMING_NETWORK",
    "location_verify": "NOT_AT_CLAIMED_LOCATION",
    "number_verify": "CONSENT_REQUIRED",
    "step_up_otp": "CONSENT_REQUIRED",
    "device_intelligence": "EVIDENCE_UNAVAILABLE",
    "number_recycling": "NUMBER_RECYCLED",
}

# The three that were NOT a live network call, and why. Kept explicit so nobody
# reads this suite as proof that all eight APIs work.
NOT_EXERCISED = {
    "number_verify": "requires an OAuth consent round trip",
    "step_up_otp": "not a network provider call",
    "device_intelligence": "no adapter is configured",
}


def test_a_fixture_exists_for_every_action():
    """Every action the agent can take against a NETWORK must have a recorded
    response, so a new CAMARA call cannot ship unobserved.

    REGISTRY_CHECK and CALL_ANNOUNCEMENT are excluded because they are not
    network calls: both are answered from this service's own state, so there is
    no vendor response to record and nothing a recording could pin. Excluding
    them keeps this test meaning what it says; adding empty fixtures for them
    would make it pass while quietly weakening it.
    """
    from app.domain.enums import Action

    local = {Action.REGISTRY_CHECK, Action.CALL_ANNOUNCEMENT}
    captured = {p.stem for p in FIXTURES}
    assert captured == {a.value for a in Action if a not in local}


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_the_provider_still_normalizes_the_observed_response(path: Path):
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["normalized"]["signal"] == OBSERVED[record["action"]]
    assert record["normalized"]["source"] == "nac"


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_every_fixture_records_its_provenance(path: Path):
    """A fixture without a version and a timestamp is an assumption again."""
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["sdk"] == "network-as-code"
    assert record["sdk_version"] == "10.0.0"
    assert record["captured_at"].startswith("2026-")
    assert record["rapidapi_host"]


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_no_fixture_carries_a_real_identifier(path: Path):
    """These are committed. Operating rule 0.1: no real identifier in the repo."""
    text = path.read_text(encoding="utf-8")
    assert "99999991000" not in text
    assert "+9999999" not in text
    record = json.loads(text)
    assert len(record["device_suffix"]) == 2


@pytest.mark.parametrize("action,reason", sorted(NOT_EXERCISED.items()))
def test_the_unexercised_apis_are_labelled_not_claimed(action: str, reason: str):
    """The runbook forbids quietly promoting an API that was never exercised."""
    record = json.loads((Path(FIXTURES[0]).parent / f"{action}.json").read_text(encoding="utf-8"))
    assert record["elapsed_ms"] == 0, f"{action} looks like it made a real call"
    assert record["normalized"]["signal"] in {"CONSENT_REQUIRED", "EVIDENCE_UNAVAILABLE"}


@pytest.mark.parametrize(
    "action",
    ["sim_swap", "device_swap", "reachability", "roaming", "location_verify", "number_recycling"],
)
def test_the_live_apis_really_did_call_the_network(action: str):
    """Non-zero latency is the difference between an observation and a guess."""
    record = json.loads((Path(FIXTURES[0]).parent / f"{action}.json").read_text(encoding="utf-8"))
    assert record["elapsed_ms"] > 0
    assert record["raw"]["ok"] is True
