from __future__ import annotations

import asyncio

from app.chain.models import EvidenceLink
from app.domain.enums import API_LABEL, Action, Result
from app.domain.schemas import VerificationRequest

# Consent basis recorded per action (privacy-by-design audit trail).
_CONSENT = {
    Action.NUMBER_VERIFY: "simulator authorization",
    Action.SIM_SWAP: "3-legged CIBA token",
    Action.DEVICE_SWAP: "3-legged CIBA token",
    Action.LOCATION_VERIFY: "3-legged CIBA token",
    Action.REACHABILITY: "3-legged CIBA token",
    Action.ROAMING: "3-legged CIBA token",
    Action.DEVICE_INTELLIGENCE: "device reputation lookup",
}

# A scenario maps an Action -> (Result, signal, detail sentence).
Scenario = dict[Action, tuple[Result, str, str]]

_CLEAN: Scenario = {
    Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH", "number matches the device"),
    Action.SIM_SWAP: (Result.PASS, "SIM_STABLE", "no SIM change on record"),
    Action.DEVICE_SWAP: (Result.PASS, "DEVICE_STABLE", "same device as usual"),
    Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION", "at claimed address"),
    Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL", "normal connectivity"),
    Action.ROAMING: (Result.PASS, "HOME_NETWORK", "on home network"),
    Action.DEVICE_INTELLIGENCE: (Result.PASS, "DEVICE_TRUSTED", "good device reputation"),
}

# Scripted demo scenarios, keyed by phone number.
SCENARIOS: dict[str, Scenario] = {
    # Act I — clean signup (low-friction number match clears instantly)
    "+962790000001": _CLEAN,
    "+99999991001": _CLEAN,
    # Act II — the ghost: SIM swapped 41 min ago, new device, wrong location
    "+962790000002": {
        Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH", "number matches the device"),
        Action.SIM_SWAP: (Result.FLAG, "SIM_SWAPPED", "swap detected 41 min ago"),
        Action.DEVICE_SWAP: (Result.FLAG, "DEVICE_SWAPPED", "new handset, first seen today"),
        Action.LOCATION_VERIFY: (Result.FLAG, "NOT_AT_CLAIMED_LOCATION", "not at claimed address"),
        Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL", "normal connectivity"),
        Action.ROAMING: (Result.PASS, "HOME_NETWORK", "on home network"),
        Action.DEVICE_INTELLIGENCE: (Result.FLAG, "DEVICE_RISKY", "device linked to prior fraud"),
    },
    "+99999991000": {
        Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH", "number matches the device"),
        Action.SIM_SWAP: (Result.FLAG, "SIM_SWAPPED", "swap detected 41 min ago"),
        Action.DEVICE_SWAP: (Result.FLAG, "DEVICE_SWAPPED", "new handset, first seen today"),
        Action.LOCATION_VERIFY: (Result.FLAG, "NOT_AT_CLAIMED_LOCATION", "not at claimed address"),
        Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL", "normal connectivity"),
        Action.ROAMING: (Result.PASS, "HOME_NETWORK", "on home network"),
        Action.DEVICE_INTELLIGENCE: (Result.FLAG, "DEVICE_RISKY", "device linked to prior fraud"),
    },
    # Act III — the invisible: no bank record, but 6 years of SIM tenure clears them
    "+962790000003": {
        Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH", "number matches the device"),
        Action.SIM_SWAP: (Result.PASS, "SIM_STABLE", "SIM active 6 years, no swap"),
        Action.DEVICE_SWAP: (Result.PASS, "DEVICE_STABLE", "same device for years"),
        Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION", "matches stable home cell"),
        Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL", "normal connectivity"),
        Action.ROAMING: (Result.PASS, "HOME_NETWORK", "on home network"),
        Action.DEVICE_INTELLIGENCE: (Result.PASS, "DEVICE_TRUSTED", "good device reputation"),
    },
    "+99999991002": {
        Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH", "number matches the device"),
        Action.SIM_SWAP: (Result.PASS, "SIM_STABLE", "SIM active 6 years, no swap"),
        Action.DEVICE_SWAP: (Result.PASS, "DEVICE_STABLE", "same device for years"),
        Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION", "matches stable home cell"),
        Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL", "normal connectivity"),
        Action.ROAMING: (Result.PASS, "HOME_NETWORK", "on home network"),
        Action.DEVICE_INTELLIGENCE: (Result.PASS, "DEVICE_TRUSTED", "good device reputation"),
    },
    # Reverse Isnad — GENUINE caller: the real institution line, network-attested
    "+96265000000": {
        Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH", "caller ID matches network line"),
        Action.SIM_SWAP: (Result.PASS, "SIM_STABLE", "institution line, no recent swap"),
        Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL", "normal connectivity"),
        Action.ROAMING: (Result.PASS, "HOME_NETWORK", "calling from home network"),
        Action.DEVICE_INTELLIGENCE: (Result.PASS, "DEVICE_TRUSTED", "known good line"),
    },
    # Reverse Isnad — SPOOFED caller: fake "bank officer", number is spoofed / VoIP
    "+96279999999": {
        Action.NUMBER_VERIFY: (Result.FLAG, "NUMBER_MISMATCH", "caller ID is not associated with this device"),
        Action.SIM_SWAP: (Result.INFO, "LOCATION_UNKNOWN", "no SIM record for presented number"),
        Action.REACHABILITY: (Result.FLAG, "REACHABLE_BOTPATTERN", "VoIP / burner pattern"),
        Action.ROAMING: (Result.INFO, "ROAMING_NETWORK", "roaming status is inconsistent with the claimed line"),
        Action.DEVICE_INTELLIGENCE: (Result.FLAG, "DEVICE_RISKY", "number linked to scam reports"),
    },
}


# Demo affordance: phones "tripped" to simulate a mid-session SIM/device swap.
# Lets the stage demo swap a SIM live and watch the session die.
TRIPPED: set[str] = set()


def trip_swap(phone: str) -> None:
    TRIPPED.add(phone)


def untrip_swap(phone: str) -> None:
    TRIPPED.discard(phone)


class MockProvider:
    """Deterministic, scriptable provider for tests and the on-stage demo.

    Runs the exact same agent code path as production — only the evidence source
    differs. Unknown numbers fall back to a clean scenario.
    """

    def __init__(self, scenarios: dict[str, Scenario] | None = None, step_delay_ms: int = 0):
        self.scenarios = scenarios or SCENARIOS
        # step_delay_ms > 0 paces the console so each link reveals visibly on stage.
        self.step_delay_ms = step_delay_ms

    async def gather(self, action: Action, request: VerificationRequest) -> EvidenceLink:
        if self.step_delay_ms:
            await asyncio.sleep(self.step_delay_ms / 1000)
        # A tripped phone now reports a fresh swap (mid-session attack simulation).
        if request.phone_number in TRIPPED and action in (Action.SIM_SWAP, Action.DEVICE_SWAP):
            signal = "SIM_SWAPPED" if action == Action.SIM_SWAP else "DEVICE_SWAPPED"
            return EvidenceLink(
                step=0, action=action, api=API_LABEL[action], result=Result.FLAG,
                signal=signal, detail="swap detected mid-session",
                consent_basis=_CONSENT.get(action, "n/a"), source="mock", latency_ms=40,
            )
        scenario = self.scenarios.get(request.phone_number, _CLEAN)
        result, signal, detail = scenario.get(
            action, (Result.INFO, "LOCATION_UNKNOWN", "no data for this check")
        )
        cost_ms = int(45 * (1 + list(Action).index(action) % 3))
        return EvidenceLink(
            step=0,  # assigned by the investigator when added to the chain
            action=action,
            api=API_LABEL[action],
            result=result,
            signal=signal,
            detail=detail,
            consent_basis=_CONSENT.get(action, "n/a"),
            source="mock",
            latency_ms=cost_ms,
        )
