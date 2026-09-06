from __future__ import annotations

import asyncio
from datetime import timedelta

from app.chain.models import EvidenceLink
from app.domain.enums import API_LABEL, Action, Result
from app.domain.schemas import VerificationRequest
from app.providers import timing as timing_lib
from app.providers.vocabulary import detail_for, window_hours

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

# Device Intelligence has no Nokia adapter: `docs/nac/device_intelligence.json`
# came back INFO / EVIDENCE_UNAVAILABLE. So a reputation verdict is not a thing
# this system can be told, and no scenario may assert one.
_DI_UNAVAILABLE = (Result.INFO, "EVIDENCE_UNAVAILABLE")

# A scenario maps an Action -> (Result, signal). The sentence comes from
# _NAC_DETAIL, so a fixture can only ever say what the network says.
Scenario = dict[Action, tuple[Result, str]]

_CLEAN: Scenario = {
    Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH"),
    Action.SIM_SWAP: (Result.PASS, "SIM_STABLE"),
    Action.DEVICE_SWAP: (Result.PASS, "DEVICE_STABLE"),
    Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION"),
    Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL"),
    Action.ROAMING: (Result.PASS, "HOME_NETWORK"),
    Action.DEVICE_INTELLIGENCE: _DI_UNAVAILABLE,
}

# Act II — the ghost: a swap inside the window, a new device, wrong location.
# The acts are told apart by WHICH checks come back adverse, never by prose:
# every scenario here draws from the same seventeen network sentences.
_GHOST: Scenario = {
    Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH"),
    Action.SIM_SWAP: (Result.FLAG, "SIM_SWAPPED"),
    Action.DEVICE_SWAP: (Result.FLAG, "DEVICE_SWAPPED"),
    Action.LOCATION_VERIFY: (Result.FLAG, "NOT_AT_CLAIMED_LOCATION"),
    Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL"),
    Action.ROAMING: (Result.PASS, "HOME_NETWORK"),
    Action.DEVICE_INTELLIGENCE: _DI_UNAVAILABLE,
}

# Act III — the invisible: no bank record, but the network has nothing against
# them. Every check the operator can answer comes back clean.
_INVISIBLE: Scenario = {
    Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH"),
    Action.SIM_SWAP: (Result.PASS, "SIM_STABLE"),
    Action.DEVICE_SWAP: (Result.PASS, "DEVICE_STABLE"),
    Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION"),
    Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL"),
    Action.ROAMING: (Result.PASS, "HOME_NETWORK"),
    Action.DEVICE_INTELLIGENCE: _DI_UNAVAILABLE,
}

# Act V — the gap: consent withheld and a provider that cannot answer.
# The chain has a hole in it rather than a failed check — CHALLENGE, not DECLINE.
_GAP: Scenario = {
    Action.NUMBER_VERIFY: (Result.INFO, "CONSENT_REQUIRED"),
    Action.SIM_SWAP: (Result.INFO, "PROVIDER_UNAVAILABLE"),
    Action.DEVICE_SWAP: (Result.INFO, "EVIDENCE_UNAVAILABLE"),
    Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION"),
    Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL"),
    Action.ROAMING: (Result.PASS, "HOME_NETWORK"),
    Action.DEVICE_INTELLIGENCE: _DI_UNAVAILABLE,
}

# Act VI — the lost phone: a real customer who replaced a SIM inside the window.
# A rules engine sees SIM_SWAPPED and declines. The agent keeps investigating,
# finds the same handset still on the line and the device at the claimed
# location, and lands on CHALLENGE with a DEGRADED chain — a step-up instead of
# a false decline. Note what the network CANNOT tell us here: whether the swap
# was three days ago or three minutes. Only that it was inside the window.
_LOST_PHONE: Scenario = {
    Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH"),
    Action.SIM_SWAP: (Result.FLAG, "SIM_SWAPPED"),
    Action.DEVICE_SWAP: (Result.PASS, "DEVICE_STABLE"),
    Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION"),
    Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL"),
    Action.ROAMING: (Result.INFO, "ROAMING_NETWORK"),
    Action.DEVICE_INTELLIGENCE: _DI_UNAVAILABLE,
}

# Scripted demo scenarios, keyed by phone number.
SCENARIOS: dict[str, Scenario] = {
    # Act I — clean signup (low-friction number match clears instantly)
    "+962790000001": _CLEAN,
    "+99999991001": _CLEAN,
    "+962790000002": _GHOST,
    "+99999991000": _GHOST,
    "+962790000003": _INVISIBLE,
    "+99999991002": _INVISIBLE,
    "+962790000005": _GAP,
    "+99999991005": _GAP,
    "+962790000006": _LOST_PHONE,
    "+99999991006": _LOST_PHONE,
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
        Action.NUMBER_VERIFY: (Result.INFO, "EVIDENCE_UNAVAILABLE"),
        Action.SIM_SWAP: (Result.INFO, "EVIDENCE_UNAVAILABLE"),
        Action.DEVICE_SWAP: (Result.INFO, "EVIDENCE_UNAVAILABLE"),
        Action.LOCATION_VERIFY: (Result.INFO, "EVIDENCE_UNAVAILABLE"),
        Action.REACHABILITY: (Result.INFO, "EVIDENCE_UNAVAILABLE"),
        Action.ROAMING: (Result.INFO, "EVIDENCE_UNAVAILABLE"),
        Action.DEVICE_INTELLIGENCE: _DI_UNAVAILABLE,
    },
    # Reverse Isnad — GENUINE caller: the real institution line, network-attested
    "+96265000000": {
        Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH"),
        Action.SIM_SWAP: (Result.PASS, "SIM_STABLE"),
        Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL"),
        Action.ROAMING: (Result.PASS, "HOME_NETWORK"),
        Action.DEVICE_INTELLIGENCE: _DI_UNAVAILABLE,
    },
    # Reverse Isnad — SPOOFED caller: a fake "bank officer" presenting a number
    # the network does not place on the device that is calling.
    #
    # This scenario used to be carried by DEVICE_RISKY ("number linked to scam
    # reports") and REACHABLE_BOTPATTERN ("VoIP / burner pattern"). Neither is a
    # reading any CAMARA API returns, and a telecom judge would have known it.
    # The decline now rests on two facts an operator can actually give you:
    #
    #   Number Verification -> the network does not place this number on the
    #                          calling device            (NUMBER_MISMATCH, +1.5)
    #   SIM Swap            -> that line changed SIM inside the max_age window
    #                                                     (SIM_SWAPPED,     +2.2)
    #
    # Two independent checks disagreeing with the caller is exactly the
    # corroboration the policy demands before it will decline anyone.
    "+96279999999": {
        Action.NUMBER_VERIFY: (Result.FLAG, "NUMBER_MISMATCH"),
        Action.SIM_SWAP: (Result.FLAG, "SIM_SWAPPED"),
        Action.DEVICE_SWAP: (Result.FLAG, "DEVICE_SWAPPED"),
        Action.LOCATION_VERIFY: (Result.INFO, "LOCATION_UNKNOWN"),
        Action.REACHABILITY: (Result.FLAG, "REACHABLE_UNAVAILABLE"),
        Action.ROAMING: (Result.INFO, "ROAMING_NETWORK"),
        Action.DEVICE_INTELLIGENCE: _DI_UNAVAILABLE,
    },
}


# Demo affordance: phones "tripped" to simulate a mid-session SIM/device swap.
# Lets the stage demo swap a SIM live and watch the session die.
TRIPPED: set[str] = set()

# --- authored swap dates -----------------------------------------------------
#
# Offsets from the observation instant, not absolute dates: an absolute date in
# a fixture goes stale, and a stale "swapped 400 days ago" that is really 800
# days ago is a fixture quietly lying about its own scenario. Ages stay
# deterministic because they are computed from one instant per run.
#
# `None` means the operator answered with no date — the case a UI must show as
# unknown rather than as "never changed".
_FRESH_SWAP = timedelta(hours=6)
_OLD_CHANGE = timedelta(days=417)

_MOCK_SWAP_AGE: dict[str, timedelta | None] = {
    "SIM_SWAPPED": _FRESH_SWAP,
    "DEVICE_SWAPPED": _FRESH_SWAP,
    "SIM_STABLE": _OLD_CHANGE,
    "DEVICE_STABLE": _OLD_CHANGE,
}

# Numbers whose date operation answers with an explicit null, so the "operator
# has the boolean but no date" path is reachable on stage.
NO_DATE_NUMBERS: set[str] = {"+962790000005", "+99999991005"}

# The contradiction observed on Nokia's hosted simulator on 2026-09-06:
# `device_swap.check` said a change happened inside a 24-hour window while
# `device_swap.retrieve_date` returned a date nineteen days old. Reproduced
# here as a VISIBLY AUTHORED fixture so the UI path can be demonstrated without
# a hosted call — never presented as an observation.
DISAGREEING_NUMBERS: set[str] = {"+962790000002", "+99999991000"}
_DISAGREEING_AGE = timedelta(days=19)

# Authored network conditions. `None` confidence is deliberate: an operator
# that reports a level without one is the case a UI turns into a fake 100%.
NO_CONGESTION_DATA: set[str] = {"+962790000005", "+99999991005"}
_MOCK_CONGESTION: dict[str, tuple[str, int | None]] = {
    "+962790000002": ("High", None),
    "+99999991000": ("High", None),
    "+962790000001": ("Low", 82),
    "+99999991001": ("Low", 82),
}


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

    async def enrich_timing(self, action: Action, request: VerificationRequest, signal: str):
        """The mock's own `retrieve-date`, with the same contract as the real one.

        It is a separate call here too — the investigator pays for it separately
        — so an offline rehearsal exercises the same accounting as a hosted run.
        """
        if action not in timing_lib.TIMED_ACTIONS:
            return timing_lib.unsupported(action, "no date operation for this action")
        retrieved_at = timing_lib.now_utc()
        if request.phone_number in NO_DATE_NUMBERS:
            return timing_lib.normalize(action, None, retrieved_at)
        age = _MOCK_SWAP_AGE.get(signal)
        if age is None:
            return timing_lib.normalize(action, None, retrieved_at)
        if request.phone_number in DISAGREEING_NUMBERS and signal in timing_lib.CHANGED_SIGNALS:
            age = _DISAGREEING_AGE
        return timing_lib.normalize(action, retrieved_at - age, retrieved_at)

    # --- network conditions: an authored operator, clearly labelled ----------

    def create_congestion_subscription(
        self, phone_number: str, callback_url: str, callback_token: str, expires_at
    ) -> str:
        return "mock-congestion-" + str(abs(hash(phone_number)) % 100000)

    def delete_congestion_subscription(self, provider_id: str) -> None:
        return None

    def query_congestion(self, phone_number: str, start=None, end=None) -> list[dict]:
        """A scripted reading, including the two shapes a UI most often gets
        wrong: nothing at all, and a level with no confidence attached."""
        if phone_number in NO_CONGESTION_DATA:
            return []
        now = timing_lib.now_utc()
        first = start or now
        second = (end or now + timedelta(minutes=15))
        level, confidence = _MOCK_CONGESTION.get(phone_number, ("Low", 82))
        return [
            {"start": first, "stop": second, "level": level, "confidence": confidence}
        ]

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
                detail=detail_for(signal),
                consent_basis=_CONSENT.get(action, "n/a"),
                source="mock",
                latency_ms=40,
                max_age_hours=window_hours(action),
            )
        cost_ms = int(45 * (1 + list(Action).index(action) % 3))
        # A location verdict answers a claim. With no claimed_location on the
        # request there is nothing to check the network against, so no scripted
        # match/mismatch may stand in for one — that would be fabricating the
        # very fact this check exists to attest. Checked before fixture
        # selection so it applies to every scenario, not only the clean one.
        if action == Action.LOCATION_VERIFY and request.context.claimed_location is None:
            return EvidenceLink(
                step=0,
                action=action,
                api=API_LABEL[action],
                result=Result.INFO,
                signal="EVIDENCE_UNAVAILABLE",
                detail=detail_for("EVIDENCE_UNAVAILABLE"),
                consent_basis=_CONSENT.get(action, "n/a"),
                source="mock",
                latency_ms=cost_ms,
                max_age_hours=window_hours(action),
            )
        scenario = self.scenarios.get(request.phone_number, _CLEAN)
        result, signal = scenario.get(action, (Result.INFO, "EVIDENCE_UNAVAILABLE"))
        detail = detail_for(signal, connectivity="SMS")
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
            max_age_hours=window_hours(action),
        )
