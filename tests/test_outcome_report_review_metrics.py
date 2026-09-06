"""I12 — review metrics and an optional business-impact worksheet, added on
top of P5's existing offline report. No metric here changes a policy, a
provider call, or any past or new merchant verdict — report-only.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.chain.models import Verdict
from app.db import challenges, outcomes, store
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

    token = current_owner.set(owner_hash("review-metrics-key"))
    yield
    current_owner.reset(token)


def _owner() -> str:
    from app.ownership import owner_hash

    return owner_hash("review-metrics-key")


def _seed(chain_id: str, decision: Decision = Decision.ALLOW) -> None:
    store.save(
        Verdict(
            decision=decision,
            chain_grade=ChainGrade.DEGRADED,
            confidence=0.4,
            hypothesis="legit",
            reason="",
            chain_id=chain_id,
            provider_sources=["nac"],
        )
    )


def test_manually_accepted_orders_are_counted():
    _seed("chn_rm_1")
    outcomes.report(
        chain_id="chn_rm_1",
        dimension="order_status",
        value="ACCEPTED",
        basis=None,
        occurred_at=datetime.now(UTC),
        late_report=False,
        supersedes_event_id=None,
        idempotency_key="k-rm-1",
        fingerprint="fp-rm-1",
    )

    report = report_script.build_report(_owner())
    assert report["review_metrics"]["manually_accepted_orders"] >= 1


def test_challenge_completion_time_is_averaged_over_completed_attempts():
    _seed("chn_rm_2")
    outcome = challenges.create_attempt(
        chain_id="chn_rm_2", method="manual_review", idempotency_key="k-rm-2a", fingerprint="fp-rm-2a"
    )
    attempt_id = outcome.response["attempt_id"]
    challenges.report_event(
        chain_id="chn_rm_2",
        attempt_id=attempt_id,
        result="PASSED",
        idempotency_key="k-rm-2b",
        fingerprint="fp-rm-2b",
    )

    report = report_script.build_report(_owner())
    assert report["review_metrics"]["challenge_completion_time_seconds"] is not None
    assert report["review_metrics"]["challenge_completion_time_seconds"] >= 0


def test_no_worksheet_without_explicit_assumptions():
    _seed("chn_rm_3")
    report = report_script.build_report(_owner())
    assert report["business_impact_worksheet"] is None


def test_a_worksheet_with_assumptions_is_report_only():
    _seed("chn_rm_4")
    report = report_script.build_report(
        _owner(), review_cost=5.0, margin_percent=20.0, currency="USD"
    )
    worksheet = report["business_impact_worksheet"]
    assert worksheet is not None
    assert worksheet["currency"] == "USD"
    assert worksheet["assumptions"]["review_cost"] == 5.0
    assert "range" in worksheet
    assert "this is a scenario assumption, not recovered revenue" in worksheet["disclaimer"].lower()
