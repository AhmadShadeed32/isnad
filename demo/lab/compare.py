"""I2 — one-fact counterfactual explorer.

Changes exactly one input on an existing scenario's request and reruns it
through the same shared runner (same deterministic planner, same full
policy), so the comparison reflects a real recomputation of every affected
choice and grade — never a rewritten score alone. Deliberately does not
reuse `app/policy/counterfactual.py`: that module compares pricing/OTP
assumptions, not alternate network evidence, and is not a decision engine.

The only variant implemented is removing the customer's claimed location.
`MockProvider`'s fixtures are keyed by phone number as a whole fixed
scenario, not decomposable per field, so the honestly-supportable "one fact
changed, rest fixed" variants are the ones the investigator itself branches
on directly from the request — this is P1's own zero-SDK-call missing-claim
guarantee, exercised as a counterfactual rather than invented network
answers under an unchanged phone number.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.api.routes_console import DEMO_ACTS
from demo.lab.runner import SCENARIO_IDS, run_scenario


class NoClaimedLocation(ValueError):
    """The base scenario has no claimed_location to remove, so there is no
    single-fact variant to run — asking for one would silently pick a
    different, unrelated change instead."""


@dataclass
class Comparison:
    base_run_id: str
    variant_run_id: str
    changed_field: str
    before_value: str | None
    after_value: str | None
    base_outcome: dict
    variant_outcome: dict
    policy_digest: str
    effect: str  # "changed" | "no_observed_effect"

    def to_dict(self) -> dict:
        return asdict(self)


async def compare_missing_location_claim(scenario_id: str) -> Comparison:
    if scenario_id not in SCENARIO_IDS:
        from demo.lab.runner import UnknownScenario

        raise UnknownScenario(scenario_id)

    base_request = DEMO_ACTS[SCENARIO_IDS[scenario_id]]
    if base_request.context.claimed_location is None:
        raise NoClaimedLocation(scenario_id)

    base = await run_scenario(scenario_id)

    variant_request = base_request.model_copy(deep=True)
    variant_request.context.claimed_location = None
    variant = await run_scenario(scenario_id, request_override=variant_request)

    effect = "no_observed_effect" if base.outcome == variant.outcome else "changed"
    return Comparison(
        base_run_id=base.run_id,
        variant_run_id=variant.run_id,
        changed_field="context.claimed_location",
        before_value="present",
        after_value=None,
        base_outcome=base.outcome,
        variant_outcome=variant.outcome,
        policy_digest=base.policy_digest,
        effect=effect,
    )
