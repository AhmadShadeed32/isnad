"""I9 — judge-controlled scenario challenge.

A small, versioned, authored case set built entirely on I2/I4's shared
runner and fault wrapper. A judge selects a case id; nothing else (no raw
phone number, no provider response, no threshold, no free-text task) ever
reaches the investigator. This is an authored set with stated limitations,
not independent ground truth or a statistically held-out test.
"""

from __future__ import annotations

import random
from pathlib import Path

from app.domain.schemas import RequestContext, VerificationRequest
from demo.lab.faults import FaultInjectingProvider
from demo.lab.runner import LabRun, run_scenario

CASES: dict[str, dict] = {
    "legitimate_sim_replacement": {
        "scenario_id": "replacement",
        "description": "A genuine SIM replacement, handset unchanged. Expected: CHALLENGE.",
    },
    "clean_checkout": {
        "scenario_id": "clean",
        "description": "Every check comes back clean. Expected: ALLOW.",
    },
    "two_adverse_signals": {
        "scenario_id": "ghost",
        "description": "A SIM swap, a new device, and a claimed location the network disputes. Expected: CHALLENGE or DECLINE.",
    },
    "absent_location_claim": {
        "scenario_id": "replacement",
        "description": "The same SIM-replacement case, but the customer never claimed a location.",
        "remove_claimed_location": True,
    },
    "provider_outage": {
        "scenario_id": "replacement",
        "description": "The network cannot answer at all. Expected: unresolved, not a fabricated pass.",
        "fault_profile": "unavailable",
    },
}


class UnknownCase(ValueError):
    """The requested case id is not in the authored set — reject before doing
    any work, the same as an unknown scenario id."""


async def run_case(case_id: str, *, planner=None, policy_path: Path | None = None) -> LabRun:
    if case_id not in CASES:
        raise UnknownCase(case_id)
    case = CASES[case_id]
    scenario_id = case["scenario_id"]

    request_override: VerificationRequest | None = None
    if case.get("remove_claimed_location"):
        from app.api.routes_console import DEMO_ACTS
        from demo.lab.runner import SCENARIO_IDS

        request_override = DEMO_ACTS[SCENARIO_IDS[scenario_id]].model_copy(deep=True)
        request_override.context = RequestContext(
            **{**request_override.context.model_dump(), "claimed_location": None}
        )

    provider_override = None
    if case.get("fault_profile"):
        from app.providers.mock import MockProvider

        provider_override = FaultInjectingProvider(MockProvider(), profile=case["fault_profile"])

    return await run_scenario(
        scenario_id, request_override=request_override, provider_override=provider_override,
        planner=planner,
        policy_path=policy_path,
    )


def seeded_order(seed: int) -> list[str]:
    """A reproducible shuffle of the case set — same seed, same order, always."""
    ids = list(CASES.keys())
    random.Random(seed).shuffle(ids)
    return ids
