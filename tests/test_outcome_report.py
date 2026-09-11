"""P5's offline report: denominators and unknowns must stay honest.

Loaded from the script file directly (same pattern as
test_false_decline_baseline.py) so it exercises the real script, not a
reimplementation of it.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.chain.models import Verdict
from app.db import outcomes, store
from app.domain.enums import ChainGrade, Decision

_spec = importlib.util.spec_from_file_location(
    "merchant_outcome_report", Path(__file__).resolve().parents[1] / "scripts" / "merchant_outcome_report.py"
)
report_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report_script)


@pytest.fixture(autouse=True)
def _as_the_merchant():
    from app.events import current_owner
    from app.ownership import owner_hash

    token = current_owner.set(owner_hash("report-test-key"))
    yield
    current_owner.reset(token)


def _owner() -> str:
    from app.ownership import owner_hash

    return owner_hash("report-test-key")


def _seed(chain_id: str, decision: Decision, provider_sources: list[str]) -> None:
    verdict = Verdict(
        decision=decision,
        chain_grade=ChainGrade.ATTESTED_PARTIAL,
        confidence=0.1,
        hypothesis="legit",
        reason="",
        chain_id=chain_id,
        evidence_cost=1.5,
        provider_sources=provider_sources,
    )
    store.save(verdict)


def _report(chain_id: str, dimension: str, value: str, basis: str | None = None) -> str:
    fingerprint = "fp-" + chain_id + "-" + dimension + "-" + value
    outcome = outcomes.report(
        chain_id=chain_id,
        dimension=dimension,
        value=value,
        basis=basis,
        occurred_at=datetime.now(UTC),
        late_report=False,
        supersedes_event_id=None,
        idempotency_key="k-" + chain_id + "-" + dimension,
        fingerprint=fingerprint,
    )
    return outcome.response["event_id"]


def test_synthetic_chains_are_excluded_from_the_denominator():
    _seed("chn_rep_real", Decision.ALLOW, ["nac"])
    _seed("chn_rep_mock", Decision.ALLOW, ["mock"])
    _seed("chn_rep_fake", Decision.ALLOW, ["nac_fake"])

    report = report_script.build_report(_owner())

    chain_ids = {row["chain_id"] for row in report["rows"]}
    assert "chn_rep_real" in chain_ids
    assert "chn_rep_mock" not in chain_ids
    assert "chn_rep_fake" not in chain_ids


def test_missing_and_explicit_unknown_are_counted_separately():
    _seed("chn_rep_missing", Decision.ALLOW, ["nac"])
    _seed("chn_rep_unknown", Decision.ALLOW, ["nac"])
    _report("chn_rep_unknown", "order_status", "UNKNOWN")

    report = report_script.build_report(_owner())
    by_id = {row["chain_id"]: row for row in report["rows"]}

    assert by_id["chn_rep_missing"]["order_status"] is None
    assert by_id["chn_rep_unknown"]["order_status"] == "UNKNOWN"
    assert report["labelled"]["order_status"]["missing"] >= 1
    assert report["labelled"]["order_status"]["explicit_unknown"] >= 1


def test_a_passed_challenge_alone_does_not_count_as_a_false_decline_fix():
    """A challenge PASS is not a fraud label. Only an explicit
    CONFIRMED_LEGITIMATE assessment on a DECLINE chain counts."""
    _seed("chn_rep_declined", Decision.DECLINE, ["nac"])

    report = report_script.build_report(_owner())
    assert report["false_declines_among_labelled_legitimate"] == 0

    _report("chn_rep_declined", "fraud_assessment", "CONFIRMED_LEGITIMATE", basis="manual_investigation")
    report = report_script.build_report(_owner())
    assert report["false_declines_among_labelled_legitimate"] == 1


def test_an_allow_confirmed_as_fraud_counts_as_an_adverse_allow():
    _seed("chn_rep_allowed", Decision.ALLOW, ["nac"])
    _report("chn_rep_allowed", "fraud_assessment", "CONFIRMED_FRAUD", basis="customer_confirmation")

    report = report_script.build_report(_owner())
    assert report["adverse_allows_among_labelled_fraud"] == 1


def test_superseded_labels_do_not_count_as_current():
    _seed("chn_rep_corrected", Decision.ALLOW, ["nac"])
    first_id = _report("chn_rep_corrected", "order_status", "ACCEPTED")
    outcomes.report(
        chain_id="chn_rep_corrected",
        dimension="order_status",
        value="CANCELLED",
        basis=None,
        occurred_at=datetime.now(UTC),
        late_report=False,
        supersedes_event_id=first_id,
        idempotency_key="k-chn_rep_corrected-order_status-2",
        fingerprint="fp-chn_rep_corrected-order_status-2",
    )

    report = report_script.build_report(_owner())
    row = next(r for r in report["rows"] if r["chain_id"] == "chn_rep_corrected")
    assert row["order_status"] == "CANCELLED"


def test_report_is_scoped_to_the_owner():
    from app.events import current_owner
    from app.ownership import owner_hash

    _seed("chn_rep_mine", Decision.ALLOW, ["nac"])
    token = current_owner.set(owner_hash("a-different-merchant-key"))
    try:
        _seed("chn_rep_theirs", Decision.ALLOW, ["nac"])
    finally:
        current_owner.reset(token)

    report = report_script.build_report(_owner())
    chain_ids = {row["chain_id"] for row in report["rows"]}
    assert "chn_rep_mine" in chain_ids
    assert "chn_rep_theirs" not in chain_ids
