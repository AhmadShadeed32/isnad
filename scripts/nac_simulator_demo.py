"""Readiness, plan and bounded execution for the judge's paired evidence demo.

Three jobs, and the boundary between them is the point:

  * ``--readiness`` answers "is this deployment configured", entirely offline.
    It reports the installed SDK, the selected host, the supported scenarios,
    whether credentials are *present*, whether judge access is configured, and
    every limit. It never contacts Nokia, and it never prints a secret. A
    passing readiness check says **configured; Nokia connection not verified** —
    which is not the same sentence as a successful call, and must never be read
    as one.
  * The default run **plans**. Nothing external happens.
  * ``--execute`` runs one investigation through the SAME authenticated judge
    endpoint the page uses. It does not build its own investigator, its own
    provider or its own idempotency rules: a helper that bypassed the route
    would prove something about the helper.

Credentials are never command arguments. The Nokia key comes from server-side
settings; the judge access code is read from ``ISNAD_JUDGE_ACCESS_CODE`` in the
environment so it does not appear in a shell history or a screenshot.

    .venv311/bin/python scripts/nac_simulator_demo.py --readiness
    .venv311/bin/python scripts/nac_simulator_demo.py --mode mock_nokia --scenario stable_subscriber
    ISNAD_JUDGE_ACCESS_CODE=... .venv311/bin/python scripts/nac_simulator_demo.py \
        --mode nokia_simulator --scenario swapped_subscriber --execute --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from importlib import metadata

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.judge.evidence import EvidenceSource, JudgePlanner, policy_digest
from app.providers import nac_contract

ACCESS_CODE_ENV = "ISNAD_JUDGE_ACCESS_CODE"


def _sdk_version() -> str:
    try:
        return metadata.version("network_as_code")
    except metadata.PackageNotFoundError:  # pragma: no cover - not installed
        return "not installed"


def readiness() -> dict:
    """Configuration facts only. Zero external requests, zero secret values."""
    scenarios = nac_contract.paired_scenarios()
    real_configured = bool(settings.judge_real_nac_enabled and settings.nac_api_key)
    missing = []
    if settings.judge_real_nac_enabled:
        if not settings.nac_api_key:
            missing.append("ISNAD_NAC_API_KEY")
        if not settings.judge_codes:
            missing.append("ISNAD_JUDGE_ACCESS_CODES")
        if not settings.subject_pepper:
            missing.append("ISNAD_SUBJECT_PEPPER")
    return {
        "sdk": f"network_as_code=={_sdk_version()}",
        "python": sys.version.split()[0],
        "contract_version": nac_contract.contract_version(),
        "policy_digest": policy_digest(),
        "selected_host_for_judge_real_runs": settings.judge_nac_base_url,
        "selected_host_for_the_configured_provider": settings.nac_base_url,
        "gateway_host_header": settings.nac_rapidapi_host,
        "supported_scenarios": {
            name: spec["phone_number"] for name, spec in scenarios.items()
        },
        "supported_operations": sorted(nac_contract.contract()["operations"]),
        # Presence, never a value. A length or a prefix is still a leak.
        "nokia_credential_present": bool(settings.nac_api_key),
        "gemini_credential_present": bool(settings.gemini_api_key),
        "judge_access_codes_configured": bool(settings.judge_codes),
        "real_source_enabled": bool(settings.judge_real_nac_enabled),
        "limits": {
            "nac_attempts_per_run": settings.judge_nac_attempts_per_run,
            "nac_attempts_per_session": settings.judge_nac_attempts_per_session,
            "nac_attempts_per_hour": settings.judge_nac_attempts_per_hour,
            "gemini_calls_per_run": settings.judge_gemini_calls_per_run,
            "max_concurrent_real_runs": settings.judge_max_concurrent_real_runs,
            "nac_timeout_seconds": settings.nac_timeout_seconds,
            "sdk_retries": 0,
        },
        "status": (
            "configured_connection_not_verified"
            if real_configured
            else ("mock_only" if not settings.judge_real_nac_enabled else "misconfigured")
        ),
        "missing_configuration": missing,
        "note": (
            "Mock evidence needs no Nokia key and makes no request. A passing "
            "readiness check is configuration only; it is not evidence that any "
            "Nokia call has ever succeeded."
        ),
    }


def plan(mode: str, scenario: str, planner: str) -> dict:
    spec = nac_contract.contract()["scenarios"][scenario]
    operations = sorted(spec["responses"])
    return {
        "would_send": mode == EvidenceSource.NOKIA_SIMULATOR.value,
        "mode": mode,
        "scenario": scenario,
        "subscriber": spec["phone_number"],
        "planner": planner,
        "operations_available_to_the_planner": operations,
        "max_outbound_attempts": settings.judge_nac_attempts_per_run,
        "date_enrichment": "disabled in both modes so the pair stays comparable",
        "destination": (
            settings.judge_nac_base_url
            if mode == EvidenceSource.NOKIA_SIMULATOR.value
            else "local httpx.MockTransport (no socket)"
        ),
        "note": "Nothing has been sent. Re-run with --execute to perform this run.",
    }


def execute(base_url: str, mode: str, scenario: str, planner: str) -> dict:
    """One run, through the same authenticated endpoint the judge page uses."""
    # The same run id the page sends, so the journal this run writes is
    # recoverable afterwards. Without it a CLI rehearsal produces a decision
    # with no retrievable reasoning, which is the half worth keeping.
    run_id = f"cli-{mode}-{scenario}-{uuid.uuid4().hex[:8]}"
    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        session = client.post("/v1/judge/session")
        session.raise_for_status()
        token = session.json()["session"]
        headers = {"X-Judge-Session": token}
        if mode == EvidenceSource.NOKIA_SIMULATOR.value:
            code = os.environ.get(ACCESS_CODE_ENV, "").strip()
            if not code:
                raise SystemExit(
                    f"Real mode needs an organizer access code in ${ACCESS_CODE_ENV}. "
                    "It is read from the environment so it never lands in a shell "
                    "history, a process list or a screenshot."
                )
            granted = client.post("/v1/judge/access", headers=headers, json={"access_code": code})
            if granted.status_code != 200:
                raise SystemExit(f"access refused: {granted.json().get('detail')}")
        response = client.post(
            "/v1/judge/run",
            headers={
                **headers,
                "Idempotency-Key": run_id,
                "X-Console-Run-Id": run_id,
            },
            json={"evidence_source": mode, "scenario": scenario, "planner": planner},
        )
        if response.status_code != 200:
            raise SystemExit(f"run refused ({response.status_code}): {response.json()}")
        body = response.json()
    return {
        "run_id": run_id,
        "journal": f"GET /v1/console/runs/{run_id}/events (with the same judge session)",
        "decision": body["decision"],
        "chain_grade": body["chain_grade"],
        "chain_id": body["chain_id"],
        "planner_that_ran": body["planner"],
        "provider_sources": body["provider_sources"],
        "judge": body["judge"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readiness", action="store_true", help="offline configuration report")
    parser.add_argument(
        "--mode", choices=[source.value for source in EvidenceSource], default=None
    )
    parser.add_argument("--scenario", default="swapped_subscriber")
    parser.add_argument("--planner", choices=[p.value for p in JudgePlanner], default="greedy")
    parser.add_argument("--execute", action="store_true", help="actually perform the run")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    if args.readiness or args.mode is None:
        print(json.dumps(readiness(), indent=2, ensure_ascii=False))
        return 0
    if args.scenario not in nac_contract.paired_scenarios():
        raise SystemExit(
            f"unsupported scenario {args.scenario!r}; "
            f"supported: {sorted(nac_contract.paired_scenarios())}"
        )
    if not args.execute:
        print(json.dumps(plan(args.mode, args.scenario, args.planner), indent=2))
        return 0
    print(json.dumps(execute(args.base_url, args.mode, args.scenario, args.planner), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
