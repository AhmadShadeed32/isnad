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
    # Act V — the gap: consent withheld and a provider that cannot answer.
    # The chain has a hole in it rather than a failed check — CHALLENGE, not DECLINE.
    "+962790000005": {
        Action.NUMBER_VERIFY: (
            Result.INFO,
            "CONSENT_REQUIRED",
            "customer has not authorized number verification",
        ),
        Action.SIM_SWAP: (
            Result.INFO,
            "PROVIDER_UNAVAILABLE",
            "operator has not exposed SIM Swap in this market",
        ),
        Action.DEVICE_SWAP: (
            Result.INFO,
            "EVIDENCE_UNAVAILABLE",
            "no device history for this line",
        ),
        Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION", "at claimed address"),
        Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL", "normal connectivity"),
        Action.ROAMING: (Result.PASS, "HOME_NETWORK", "on home network"),
        Action.DEVICE_INTELLIGENCE: (Result.PASS, "DEVICE_TRUSTED", "good device reputation"),
    },
    "+99999991005": {
        Action.NUMBER_VERIFY: (
            Result.INFO,
            "CONSENT_REQUIRED",
            "customer has not authorized number verification",
        ),
        Action.SIM_SWAP: (
            Result.INFO,
            "PROVIDER_UNAVAILABLE",
            "operator has not exposed SIM Swap in this market",
        ),
        Action.DEVICE_SWAP: (
            Result.INFO,
            "EVIDENCE_UNAVAILABLE",
            "no device history for this line",
        ),
        Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION", "at claimed address"),
        Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL", "normal connectivity"),
        Action.ROAMING: (Result.PASS, "HOME_NETWORK", "on home network"),
        Action.DEVICE_INTELLIGENCE: (Result.PASS, "DEVICE_TRUSTED", "good device reputation"),
    },
    # Act VI — the lost phone: a real customer who replaced a SIM three days ago.
    # A rules engine sees SIM_SWAPPED and declines. The agent keeps investigating,
    # finds the same handset at the right address, and lands on CHALLENGE with a
    # DEGRADED chain — a step-up instead of a false decline.
    "+962790000006": {
        Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH", "number matches the device"),
        Action.SIM_SWAP: (Result.FLAG, "SIM_SWAPPED", "swap detected 3 days ago"),
        Action.DEVICE_SWAP: (
            Result.PASS,
            "DEVICE_STABLE",
            "same handset before and after the swap",
        ),
        Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION", "at claimed address"),
        Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL", "normal connectivity"),
        Action.ROAMING: (Result.INFO, "ROAMING_NETWORK", "on a partner network"),
        Action.DEVICE_INTELLIGENCE: (Result.PASS, "DEVICE_TRUSTED", "good device reputation"),
    },
    "+99999991006": {
        Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH", "number matches the device"),
        Action.SIM_SWAP: (Result.FLAG, "SIM_SWAPPED", "swap detected 3 days ago"),
        Action.DEVICE_SWAP: (
            Result.PASS,
            "DEVICE_STABLE",
            "same handset before and after the swap",
        ),
        Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION", "at claimed address"),
        Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL", "normal connectivity"),
        Action.ROAMING: (Result.INFO, "ROAMING_NETWORK", "on a partner network"),
        Action.DEVICE_INTELLIGENCE: (Result.PASS, "DEVICE_TRUSTED", "good device reputation"),
    },
    # Act VIII — the bank's landline. THE HONEST LIMIT, and the reason this
    # scenario exists at all.
    #
    # This is Demo Bank's switchboard: the same number the registry knows by
    # name. It is a PBX / SIP trunk, and a trunk has no SIM — so SIM Swap,
    # Device Swap and Number Verification are not "failing" here, they are
    # inapplicable. Every one of them can only answer "I have no record of this
    # subscription", because there is no subscription.
    #
    # The right outcome is a chain with a HOLE in it (UNRESOLVED), not a guess
    # in either direction. A system that returned TRUST_CALLER here would be
    # inventing an attestation no network gave it; one that returned
    # REJECT_CALLER would be declining every real bank in the country.
    # An extension inside the bank's published +9626500 DID block, so the
    # registry resolves it by prefix while the network can say nothing. Not the
    # switchboard number itself — that is already the Reverse Isnad genuine
    # caller fixture below, and two entries for one key would silently collapse.
    "+96265000123": {
        Action.NUMBER_VERIFY: (
            Result.INFO,
            "EVIDENCE_UNAVAILABLE",
            "no mobile subscription: this is a fixed line",
        ),
        Action.SIM_SWAP: (
            Result.INFO,
            "EVIDENCE_UNAVAILABLE",
            "no SIM to have been swapped: fixed line",
        ),
        Action.DEVICE_SWAP: (
            Result.INFO,
            "EVIDENCE_UNAVAILABLE",
            "no handset history for a PBX trunk",
        ),
        Action.LOCATION_VERIFY: (Result.INFO, "EVIDENCE_UNAVAILABLE", "no device to locate"),
        Action.REACHABILITY: (
            Result.INFO,
            "EVIDENCE_UNAVAILABLE",
            "reachability is a mobile-subscription concept",
        ),
        Action.ROAMING: (Result.INFO, "EVIDENCE_UNAVAILABLE", "a fixed line does not roam"),
        Action.DEVICE_INTELLIGENCE: (
            Result.INFO,
            "EVIDENCE_UNAVAILABLE",
            "no device reputation for a trunk",
        ),
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
        Action.NUMBER_VERIFY: (
            Result.FLAG,
            "NUMBER_MISMATCH",
            "caller ID is not associated with this device",
        ),
        Action.SIM_SWAP: (Result.INFO, "LOCATION_UNKNOWN", "no SIM record for presented number"),
        Action.REACHABILITY: (Result.FLAG, "REACHABLE_BOTPATTERN", "VoIP / burner pattern"),
        Action.ROAMING: (
            Result.INFO,
            "ROAMING_NETWORK",
            "roaming status is inconsistent with the claimed line",
        ),
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


def clear_tripped_swaps() -> None:
    """Clear the local-only stage simulation between complete demo runs."""
    TRIPPED.clear()


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
                step=0,
                action=action,
                api=API_LABEL[action],
                result=Result.FLAG,
                signal=signal,
                detail="swap detected mid-session",
                consent_basis=_CONSENT.get(action, "n/a"),
                source="mock",
                latency_ms=40,
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
