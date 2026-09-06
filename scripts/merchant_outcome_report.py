"""Owner-scoped offline report: has anyone told us what actually happened? (P5)

Joins each of one merchant's own signed chains to whatever outcome labels
exist for it — order status and fraud assessment, both current (non-
superseded) heads only — plus P3's own challenge-attempt status, read fresh
rather than duplicated. This is a report over what has been reported so far,
not a production accuracy claim: it states its denominator and its unknowns
rather than folding them into either label.

Excludes synthetic runs (provider_sources containing "mock" or "nac_fake").
Counts a false decline only among DECLINE chains a merchant independently
labelled CONFIRMED_LEGITIMATE, and an adverse allow only among ALLOW chains
labelled CONFIRMED_FRAUD — never inferred from a challenge outcome, an order
status, or the absence of a dispute alone.

Runs directly against the configured database (ISNAD_DATABASE_URL), not
through the HTTP API: the API's own GET is scoped to one chain at a time, and
this report needs every chain a merchant owns.

    ISNAD_MERCHANT_API_KEY=<key> .venv311/bin/python scripts/merchant_outcome_report.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SYNTHETIC_SOURCES = {"mock", "nac_fake"}


def _is_synthetic(verdict_json: str) -> bool:
    try:
        payload = json.loads(verdict_json)
    except ValueError:
        return True  # unreadable payload: exclude rather than guess
    sources = payload.get("provider_sources") or []
    return any(source in SYNTHETIC_SOURCES for source in sources)


def _evidence_cost(verdict_json: str) -> float:
    try:
        return float(json.loads(verdict_json).get("evidence_cost", 0.0))
    except (ValueError, TypeError):
        return 0.0


def build_report(owner: str) -> dict:
    from app.db.database import SessionLocal
    from app.db.models import ChainRow, ChallengeAttemptRow, MerchantOutcomeEventRow

    with SessionLocal() as session:
        chains = (
            session.query(ChainRow)
            .filter(ChainRow.owner_hash == owner)
            .order_by(ChainRow.created_at.asc())
            .all()
        )

        rows: list[dict] = []
        counts = {
            "order_status": {"labelled": 0, "explicit_unknown": 0, "missing": 0},
            "fraud_assessment": {"labelled": 0, "explicit_unknown": 0, "missing": 0},
        }
        challenge = {"opened": 0, "completed": 0, "abandoned": 0, "pending_or_expired": 0}
        false_declines = 0
        adverse_allows = 0
        evidence_cost_total = 0.0
        eligible_created_ats: list[datetime] = []

        for chain in chains:
            if _is_synthetic(chain.verdict_json):
                continue
            eligible_created_ats.append(chain.created_at)
            evidence_cost_total += _evidence_cost(chain.verdict_json)

            order = (
                session.query(MerchantOutcomeEventRow)
                .filter(
                    MerchantOutcomeEventRow.chain_id == chain.chain_id,
                    MerchantOutcomeEventRow.owner_hash == owner,
                    MerchantOutcomeEventRow.dimension == "order_status",
                    MerchantOutcomeEventRow.superseded_by.is_(None),
                )
                .first()
            )
            fraud = (
                session.query(MerchantOutcomeEventRow)
                .filter(
                    MerchantOutcomeEventRow.chain_id == chain.chain_id,
                    MerchantOutcomeEventRow.owner_hash == owner,
                    MerchantOutcomeEventRow.dimension == "fraud_assessment",
                    MerchantOutcomeEventRow.superseded_by.is_(None),
                )
                .first()
            )
            for dimension, event in (("order_status", order), ("fraud_assessment", fraud)):
                if event is None:
                    counts[dimension]["missing"] += 1
                elif event.value == "UNKNOWN":
                    counts[dimension]["explicit_unknown"] += 1
                else:
                    counts[dimension]["labelled"] += 1

            attempt = (
                session.query(ChallengeAttemptRow)
                .filter(ChallengeAttemptRow.chain_id == chain.chain_id, ChallengeAttemptRow.owner_hash == owner)
                .order_by(ChallengeAttemptRow.created_at.desc())
                .first()
            )
            if attempt is not None:
                challenge["opened"] += 1
                if attempt.status in ("PASSED", "FAILED"):
                    challenge["completed"] += 1
                elif attempt.status == "ABANDONED":
                    challenge["abandoned"] += 1
                else:
                    challenge["pending_or_expired"] += 1

            if chain.decision == "DECLINE" and fraud is not None and fraud.value == "CONFIRMED_LEGITIMATE":
                false_declines += 1
            if chain.decision == "ALLOW" and fraud is not None and fraud.value == "CONFIRMED_FRAUD":
                adverse_allows += 1

            rows.append(
                {
                    "chain_id": chain.chain_id,
                    "decision": chain.decision,
                    "created_at": chain.created_at.isoformat(),
                    "order_status": order.value if order else None,
                    "fraud_assessment": fraud.value if fraud else None,
                    "fraud_basis": fraud.basis if fraud else None,
                    "challenge_status": attempt.status if attempt else None,
                }
            )

    observation_window = None
    if eligible_created_ats:
        observation_window = {
            "earliest_chain_at": min(eligible_created_ats).isoformat(),
            "latest_chain_at": max(eligible_created_ats).isoformat(),
        }

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "eligible_denominator": len(rows),
        "observation_window": observation_window,
        "labelled": counts,
        "challenge": challenge,
        "recorded_costs": {"evidence_cost_total": round(evidence_cost_total, 4)},
        "false_declines_among_labelled_legitimate": false_declines,
        "adverse_allows_among_labelled_fraud": adverse_allows,
        "limits": [
            "Synthetic runs (mock/nac_fake provider_sources) are excluded from every count above.",
            (
                "This has no defined observation window: 'observation_window' states the actual span of "
                "eligible chains, not a fixed follow-up horizon this report enforces."
            ),
            (
                "false_declines_among_labelled_legitimate counts DECLINE chains a merchant independently "
                "labelled CONFIRMED_LEGITIMATE — never inferred from a challenge PASS, an order being "
                "fulfilled, or a lack of dispute alone."
            ),
            (
                "adverse_allows_among_labelled_fraud is the same restriction for ALLOW chains labelled "
                "CONFIRMED_FRAUD."
            ),
            "missing and explicit_unknown are counted separately per dimension and never folded together.",
            (
                "This is an observational report over whatever has been reported so far, not a production "
                "accuracy claim, and does not calibrate or retrain anything."
            ),
        ],
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=Path("/tmp/isnad-outcome-report.json"))
    args = parser.parse_args()

    api_key = os.environ.get("ISNAD_MERCHANT_API_KEY", "")
    if not api_key:
        print("ISNAD_MERCHANT_API_KEY must be set to the merchant key to report for", file=sys.stderr)
        return 1

    from app.db.database import init_db
    from app.ownership import owner_hash

    init_db()
    owner = owner_hash(api_key)
    report = build_report(owner)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out.chmod(0o600)
    print(f"wrote {args.out} — {report['eligible_denominator']} eligible chains")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
