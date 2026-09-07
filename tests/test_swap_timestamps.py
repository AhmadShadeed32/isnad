"""The operator's swap date: a second call, weaker evidence, and never the score.

The runbook's gate 5 in executable form. The load-bearing cases are the ones
where a date is absent, wrong or contradicts the boolean it sits beside: those
are where a system quietly turns "we were told nothing" into "nothing happened".
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.chain.models import EvidenceLink, EvidenceTiming, Verdict
from app.chain.vault import vault
from app.domain.enums import Action, Result
from app.domain.schemas import RequestContext, VerificationRequest
from app.providers import timing as timing_lib
from app.providers.mock import MockProvider
from tests.ui_source import read_ui_source

NOW = datetime(2026, 9, 6, 20, 0, tzinfo=UTC)
LEGACY = Path(__file__).resolve().parent / "fixtures" / "legacy_receipt_pre_swap_dates.json"


def _request(number: str = "+962790000002") -> VerificationRequest:
    """A takeover-shaped checkout, so the agent actually buys the swap checks
    whose dates this suite is about."""
    return VerificationRequest(
        phone_number=number,
        context=RequestContext(event="password_reset", account_age_days=0),
    )


# --- normalization -----------------------------------------------------------


@pytest.mark.parametrize(
    "offset_hours,expected_offset",
    [(0, 0), (2, 7200), (-5, -18000), (5.5, 19800)],
)
def test_a_timezone_offset_is_preserved_and_the_age_is_absolute(offset_hours, expected_offset):
    """Two operators can report the same instant in different offsets. The age
    must be the same number either way, or a receipt would read differently
    depending on where the operator happens to be."""
    tz = timezone(timedelta(hours=offset_hours))
    provider_time = (NOW - timedelta(hours=6)).astimezone(tz)
    result = timing_lib.normalize(Action.SIM_SWAP, provider_time, NOW)

    assert result.availability == "available"
    assert result.provider_time.utcoffset().total_seconds() == expected_offset
    assert result.age_seconds_at_decision == 6 * 3600


def test_a_null_date_is_no_date_and_never_never_swapped():
    result = timing_lib.normalize(Action.SIM_SWAP, None, NOW)

    assert result.availability == "no_date"
    assert result.provider_time is None
    assert result.age_seconds_at_decision is None
    assert "no date" in result.reason


def test_a_naive_timestamp_is_invalid_rather_than_assumed_utc():
    """Guessing UTC would invent an age that could be hours wrong."""
    naive = datetime(2026, 9, 6, 14, 0)  # noqa: DTZ001 - naiveness is the case under test
    result = timing_lib.normalize(Action.SIM_SWAP, naive, NOW)

    assert result.availability == "invalid"
    assert "timezone" in result.reason
    assert result.age_seconds_at_decision is None


def test_a_non_timestamp_is_invalid():
    assert timing_lib.normalize(Action.SIM_SWAP, "yesterday", NOW).availability == "invalid"


def test_a_timestamp_inside_the_skew_tolerance_is_accepted_and_clamped_to_zero():
    """A provider clock a minute ahead of ours is skew, not a future event."""
    result = timing_lib.normalize(Action.SIM_SWAP, NOW + timedelta(seconds=60), NOW)

    assert result.availability == "available"
    assert result.age_seconds_at_decision == 0.0


def test_a_timestamp_beyond_the_skew_tolerance_is_invalid():
    ahead = NOW + timedelta(seconds=timing_lib.FUTURE_TOLERANCE_SECONDS + 1)
    result = timing_lib.normalize(Action.SIM_SWAP, ahead, NOW)

    assert result.availability == "invalid"
    assert str(timing_lib.FUTURE_TOLERANCE_SECONDS) in result.reason


def test_the_activation_ambiguity_is_attached_to_every_usable_date():
    """"Latest change" can be an activation, not a replacement. A reader who is
    not told that will read a date as proof of a swap."""
    result = timing_lib.normalize(Action.SIM_SWAP, NOW - timedelta(days=2), NOW)

    assert result.ambiguity_key == timing_lib.AMBIGUITY_LATEST_CHANGE


def test_a_missing_monitoring_horizon_stays_unknown():
    result = timing_lib.normalize(Action.DEVICE_SWAP, None, NOW, monitored_period_days=None)

    assert result.monitored_period_days is None


def test_a_monitoring_horizon_is_carried_through_in_days():
    result = timing_lib.normalize(Action.DEVICE_SWAP, None, NOW, monitored_period_days=120)

    assert result.monitored_period_days == 120


def test_the_age_is_measured_from_the_observation_not_from_now():
    """Replaying a receipt a month later must reproduce the decision's number."""
    long_ago = datetime(2020, 1, 1, tzinfo=UTC)
    result = timing_lib.normalize(Action.SIM_SWAP, long_ago - timedelta(hours=1), long_ago)

    assert result.age_seconds_at_decision == 3600
    assert result.retrieved_at == long_ago


# --- the boolean and the date can disagree -----------------------------------


def test_a_date_outside_the_window_of_a_positive_check_is_recorded_as_disagreement():
    """Observed on Nokia's hosted simulator, 2026-09-06: `swapped: true` for a
    24-hour window beside a date nineteen days old."""
    result = timing_lib.normalize(Action.DEVICE_SWAP, NOW - timedelta(days=19), NOW)
    marked = timing_lib.with_window_agreement(result, "DEVICE_SWAPPED", max_age_hours=24)

    assert marked.disagrees_with_window is True


def test_a_date_inside_the_window_of_a_positive_check_agrees():
    result = timing_lib.normalize(Action.SIM_SWAP, NOW - timedelta(hours=6), NOW)
    marked = timing_lib.with_window_agreement(result, "SIM_SWAPPED", max_age_hours=24)

    assert marked.disagrees_with_window is False


def test_a_negative_check_has_nothing_to_disagree_with():
    """`SIM_STABLE` says no change inside the window. An old date is exactly
    what that implies, not a contradiction."""
    result = timing_lib.normalize(Action.SIM_SWAP, NOW - timedelta(days=400), NOW)
    marked = timing_lib.with_window_agreement(result, "SIM_STABLE", max_age_hours=240)

    assert marked.disagrees_with_window is None


def test_an_unavailable_date_never_claims_agreement_either_way():
    result = timing_lib.normalize(Action.SIM_SWAP, None, NOW)
    marked = timing_lib.with_window_agreement(result, "SIM_SWAPPED", max_age_hours=24)

    assert marked.disagrees_with_window is None


# --- through a real investigation --------------------------------------------


def _run(number: str, provider=None):
    from app.agent.investigator import build_investigator

    investigator = build_investigator(provider or MockProvider())
    return asyncio.run(investigator.investigate(_request(number)))


def _engine():
    from app.config import settings
    from app.policy.engine import get_engine

    return get_engine(str(settings.policy_path))


def _links(verdict, action: Action):
    return [link for link in verdict.chain if link.action == action]


def test_a_swap_link_carries_the_operator_date_and_the_check_is_untouched():
    verdict = _run("+962790000002")
    (link,) = _links(verdict, Action.SIM_SWAP)

    assert link.signal == "SIM_SWAPPED"
    assert link.result == Result.FLAG
    assert link.timing is not None
    assert link.timing.availability == "available"
    assert link.timing.source_operation == "sim_swap.retrieve_date"


def test_the_extra_call_is_charged_separately_from_the_check():
    """Hiding the date inside the boolean's cost is a receipt claiming one call
    where two were made."""
    priced = _run("+962790000002")
    engine = _engine()
    swap_links = [
        link for link in priced.chain if link.action in timing_lib.TIMED_ACTIONS
    ]
    assert swap_links
    enriched = [link for link in swap_links if link.timing.availability != "unsupported"]
    booleans = sum(engine.action_cost(link.action) for link in priced.chain)
    expected_extra = engine.enrichment_cost("swap_date") * len(enriched)

    assert priced.evidence_cost == pytest.approx(booleans + expected_extra)
    assert expected_extra > 0


def test_a_date_never_moves_the_score():
    """The belief is built from the boolean. Two runs whose only difference is
    the date must reach the same risk score."""
    engine = _engine()
    with_dates = _run("+962790000002")
    original = engine.cfg["enrichments"]["swap_date"]["enabled"]
    engine.cfg["enrichments"]["swap_date"]["enabled"] = False
    try:
        without = _run("+962790000002")
    finally:
        engine.cfg["enrichments"]["swap_date"]["enabled"] = original

    assert with_dates.confidence == without.confidence
    assert with_dates.decision == without.decision
    # Every check that ran in both moved the belief by exactly the same amount:
    # the date explains a link, it never re-weighs one.
    shared = {link.action for link in with_dates.chain} & {
        link.action for link in without.chain
    }
    assert shared
    for action in shared:
        (a,) = [link for link in with_dates.chain if link.action == action]
        (b,) = [link for link in without.chain if link.action == action]
        assert a.delta_logodds == b.delta_logodds
        assert a.signal == b.signal

    # The honest consequence of pricing the extra call: units spent on dates
    # are units not available for another check, so the enriched run bought one
    # fewer boolean — and here it therefore finished *cheaper* overall (7 vs 8)
    # rather than more expensive. That is a real trade, not a saving: the same
    # decision was reached on less corroboration. Pinned so a future change to
    # the enrichment price shows up as a test failure instead of silently
    # rebalancing what the agent can afford to look at.
    assert len(with_dates.chain) == len(without.chain) - 1
    assert with_dates.evidence_cost == 7.0
    assert without.evidence_cost == 8.0


def test_a_disabled_enrichment_spends_nothing_and_attaches_nothing():
    engine = _engine()
    original = engine.cfg["enrichments"]["swap_date"]["enabled"]
    engine.cfg["enrichments"]["swap_date"]["enabled"] = False
    try:
        verdict = _run("+962790000002")
    finally:
        engine.cfg["enrichments"]["swap_date"]["enabled"] = original

    assert all(link.timing is None for link in verdict.chain)


def test_a_budget_too_small_for_the_extra_call_says_so_rather_than_going_quiet():
    """"Not attempted" and "the operator had no date" are different facts."""
    engine = _engine()
    link = EvidenceLink(
        step=1,
        action=Action.SIM_SWAP,
        api="SIM Swap",
        result=Result.FLAG,
        signal="SIM_SWAPPED",
        detail="d",
        max_age_hours=240,
    )
    from app.agent.investigator import build_investigator

    investigator = build_investigator(MockProvider())
    spent = asyncio.run(
        investigator._enrich_timing(link, _request(), budget_left=0.5, run_id=None)
    )

    assert spent == 0.0
    assert link.timing.availability == "not_attempted"
    assert engine.enrichment_cost("swap_date") > 0.5


def test_a_provider_failure_leaves_the_boolean_evidence_exactly_as_it_was():
    from app.agent.investigator import build_investigator

    class Exploding(MockProvider):
        async def enrich_timing(self, action, request, signal):
            raise RuntimeError("operator said no")

    investigator = build_investigator(Exploding())
    verdict = asyncio.run(investigator.investigate(_request("+962790000002")))
    (link,) = _links(verdict, Action.SIM_SWAP)

    assert link.signal == "SIM_SWAPPED"
    assert link.result == Result.FLAG
    assert link.timing.availability == "invalid"
    assert "operator said no" not in json.dumps(link.timing.model_dump(mode="json"))


def test_a_provider_without_a_date_operation_is_unsupported_and_costs_nothing():
    from app.agent.investigator import build_investigator

    class Boolean(MockProvider):
        enrich_timing = None

    link = EvidenceLink(
        step=1,
        action=Action.SIM_SWAP,
        api="SIM Swap",
        result=Result.FLAG,
        signal="SIM_SWAPPED",
        detail="d",
    )
    investigator = build_investigator(Boolean())
    spent = asyncio.run(
        investigator._enrich_timing(link, _request(), budget_left=99, run_id=None)
    )

    assert spent == 0.0
    assert link.timing.availability == "unsupported"


def test_an_action_with_no_date_operation_is_never_enriched():
    verdict = _run("+962790000001")
    for link in verdict.chain:
        if link.action not in timing_lib.TIMED_ACTIONS:
            assert link.timing is None


def test_the_authored_no_date_number_reaches_the_no_date_path():
    verdict = _run("+962790000005")
    timed = [link for link in verdict.chain if link.action in timing_lib.TIMED_ACTIONS]

    assert timed
    assert all(link.timing.availability == "no_date" for link in timed)


def test_the_authored_contradiction_fixture_reproduces_the_hosted_shape():
    """A visibly authored fixture, so the disagreement UI can be demonstrated
    offline. It is never presented as an observation."""
    verdict = _run("+962790000002")
    (device,) = _links(verdict, Action.DEVICE_SWAP)

    assert device.signal == "DEVICE_SWAPPED"
    assert device.timing.disagrees_with_window is True
    assert device.timing.age_seconds_at_decision > (device.max_age_hours or 0) * 3600


# --- signatures --------------------------------------------------------------


def test_the_receipt_signed_before_this_extension_still_verifies_byte_for_byte():
    """The stored bytes are the signature's subject. Reserializing them here
    would test Pydantic, not the receipt.

    Verified against the key recorded beside the receipt — the way the offline
    verifier does it — rather than through `vault.verify_with`, which also asks
    whether *this* deployment trusts that key. That trust question is separate
    and is asserted below; a test process holding an ephemeral key would
    otherwise report a perfectly good historical signature as broken.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    fixture = json.loads(LEGACY.read_text())
    public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(fixture["public_key"]))

    public_key.verify(
        bytes.fromhex(fixture["signature"]), fixture["signed_payload"].encode("utf-8")
    )
    # And the deployment trust gate is a separate question from the mathematics.
    assert vault.trusts(fixture["public_key"]) is False


def test_an_old_receipt_reads_back_with_no_timing_rather_than_a_default_date():
    fixture = json.loads(LEGACY.read_text())
    verdict = Verdict.model_validate_json(fixture["signed_payload"])

    assert verdict.chain
    assert all(link.timing is None for link in verdict.chain)


def test_a_new_receipt_commits_to_the_date_inside_the_same_signature(tmp_path):
    """Not a sibling field: editing the date in the signed text must break the
    signature, or the metadata is decoration."""
    verdict = _run("+962790000002")
    (link,) = _links(verdict, Action.SIM_SWAP)
    assert link.timing.provider_time is not None

    payload = verdict.model_dump_json()
    signature = vault.sign(payload.encode("utf-8"))
    assert vault.verify(payload.encode("utf-8"), signature)
    assert '"timing"' in payload

    tampered = payload.replace(
        link.timing.provider_time.isoformat().replace("+00:00", "Z"), "2001-01-01T00:00:00Z"
    )
    if tampered == payload:  # serialization uses the offset form
        tampered = payload.replace(link.timing.provider_time.isoformat(), "2001-01-01T00:00:00+00:00")

    assert tampered != payload
    assert not vault.verify(tampered.encode("utf-8"), signature)


def test_tampering_with_the_disagreement_flag_breaks_the_signature():
    verdict = _run("+962790000002")
    payload = verdict.model_dump_json()
    signature = vault.sign(payload.encode("utf-8"))
    tampered = payload.replace('"disagrees_with_window":true', '"disagrees_with_window":false')

    assert tampered != payload
    assert not vault.verify(tampered.encode("utf-8"), signature)


def test_a_link_without_timing_serializes_the_field_as_null_not_as_absent():
    """Explicit null keeps "we did not ask" distinguishable from an old receipt
    written before the field existed."""
    link = EvidenceLink(
        step=1, action=Action.REACHABILITY, api="x", result=Result.PASS, signal="s", detail="d"
    )

    assert json.loads(link.model_dump_json())["timing"] is None


# --- bilingual display -------------------------------------------------------


REQUIRED_KEYS = [
    "swap_date_heading",
    "swap_date_available",
    "swap_date_age",
    "swap_date_no_date",
    "swap_date_unsupported",
    "swap_date_denied",
    "swap_date_timeout",
    "swap_date_invalid",
    "swap_date_not_attempted",
    "swap_date_may_be_activation",
    "swap_date_horizon_unknown",
    "swap_date_disagrees",
    "swap_date_separate_call",
]


@pytest.mark.parametrize("locale", ["en", "ar"])
def test_every_timing_state_has_authored_copy_in_both_languages(locale):
    dictionary = json.loads(
        (Path("app/static/i18n") / f"{locale}.json").read_text(encoding="utf-8")
    )["ui"]

    missing = [key for key in REQUIRED_KEYS if not dictionary.get(key)]
    assert missing == []


def test_every_availability_value_has_a_display_key():
    """A new availability state without copy would render a raw enum."""
    states = EvidenceTiming.model_fields["availability"].annotation.__args__
    dictionary = json.loads(Path("app/static/i18n/en.json").read_text(encoding="utf-8"))["ui"]

    for state in states:
        assert dictionary.get(f"swap_date_{state}"), state


def test_the_exact_timestamp_is_rendered_ltr_isolated():
    """Under an RTL page the bidi algorithm reorders a bare ISO timestamp at
    its neutral edges, and a reordered exact value is the wrong value."""
    judge = read_ui_source(Path("app/static/judge.html"))

    assert "appendTiming" in judge
    assert "Isnad.isolate(event.provider_time)" in judge


def test_the_date_row_is_separate_from_the_evidence_row_in_both_surfaces():
    """Merging them would present a second call as part of the first."""
    for path in ("app/static/judge.html", "app/static/console.html"):
        page = read_ui_source(Path(path))
        assert "'enrichment'" in page, path
