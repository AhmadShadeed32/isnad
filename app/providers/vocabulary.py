"""The only sentences an evidence link may carry, and where each one comes from.

Every string here is either (a) what the network returned, or (b) a derivation
from what the network returned plus the parameter we sent it. Nothing else is
allowed, and `tests/test_provider_vocabulary.py` fails the build if a fixture
ever invents a third kind.

The distinction matters on stage. A judge who asks "how do you know that?" must
get one sentence back that ends the question:

    "recent SIM swap detected"          -> the check returned swapped=true
    "SIM swap inside the last 240 h"    -> ...and 240 h is the max_age we sent

CAMARA SIM Swap and Device Swap answer a **boolean against a window**. They do
not return a timestamp, so no link may say "swapped 41 minutes ago", "SIM active
6 years" or "new handset, first seen today". Those were fixture prose, and any
operator in the room would have known it. The window is the strongest true
statement available, and it is strong enough: it is the same fact, bounded.

`SIM Swap` does publish a `retrieve-date` endpoint that would return the actual
change date. This system does not call it. If it ever does, the timestamp
becomes sayable — and that is the only way it becomes sayable.
"""

from __future__ import annotations

from app.config import settings
from app.domain.enums import Action

# Signals with no CAMARA source at all. Nokia Network as Code exposes no device
# reputation product (`docs/nac/device_intelligence.json` came back INFO /
# EVIDENCE_UNAVAILABLE), and no reachability response can characterise a line as
# a VoIP burner. They stay priced in policy.yaml as RESERVED so a future
# provider has a weight to inherit; nothing may emit them today.
UNBACKED_SIGNALS = frozenset({"DEVICE_TRUSTED", "DEVICE_RISKY", "REACHABLE_BOTPATTERN"})


def window_hours(action: Action) -> float | None:
    """The age window this action's question covered, if it has one.

    Mirrors the max_age arguments the live adapter passes, and lives beside the
    sentence that quotes it: a link that SAYS "in the last 240 h" must also
    CARRY 240 in `max_age_hours`, or the receipt shows a window the call did not
    use. Mock links carry it too — the fixture is answering the same question.
    """
    if action in (Action.SIM_SWAP, Action.DEVICE_SWAP):
        return float(settings.nac_max_age_hours)
    if action == Action.LOCATION_VERIFY:
        return settings.nac_location_max_age_seconds / 3600.0
    return None


def _window() -> str:
    """The max_age the swap checks are actually called with."""
    return f"{settings.nac_max_age_hours} h"


def detail_for(signal: str, *, connectivity: str | None = None, countries: str | None = None) -> str:
    """The sentence for a signal, derived from the response and our parameters."""
    if signal == "REACHABLE_NORMAL":
        return f"device reachable via {connectivity or 'network connection'}"
    if signal == "ROAMING_NETWORK":
        return f"device is roaming{f' ({countries})' if countries else ''}"
    return _DETAIL[signal]


# Fixed sentences. The two swap APIs carry their window because the window is
# the whole content of the answer.
_DETAIL: dict[str, str] = {
    # Number Verification — the network places (or does not place) this number
    # on the device making the request.
    "NUMBER_MATCH": "network number matches the provided number",
    "NUMBER_MISMATCH": "network number does not match the provided number",
    "CONSENT_REQUIRED": "number verification requires user consent",
    # SIM Swap — boolean against max_age. Bounded, never dated.
    "SIM_STABLE": f"no SIM swap in the last {_window()}",
    "SIM_SWAPPED": f"SIM swap inside the last {_window()}",
    # Device Swap — same shape, same bound.
    "DEVICE_STABLE": f"no device swap in the last {_window()}",
    "DEVICE_SWAPPED": f"device swap inside the last {_window()}",
    # Location Verification — a verdict against the claimed circle.
    "AT_CLAIMED_LOCATION": "device is at the claimed location",
    "NOT_AT_CLAIMED_LOCATION": "device is not at the claimed location",
    "LOCATION_PARTIAL": "device partially overlaps the claimed area",
    "LOCATION_UNKNOWN": "fresh location evidence is unavailable",
    # Device Reachability / Roaming Status.
    "REACHABLE_UNAVAILABLE": "device is not reachable from the network",
    "HOME_NETWORK": "device is on its home network",
    # The network could not answer. This is a hole in the chain, not a finding.
    "PROVIDER_UNAVAILABLE": "provider request failed",
    "EVIDENCE_UNAVAILABLE": "provider could not produce evidence for this device",
}

# Signals that carry a derived argument and so are not in the fixed table.
_DERIVED = frozenset({"REACHABLE_NORMAL", "ROAMING_NETWORK"})

SPEAKABLE_SIGNALS = frozenset(_DETAIL) | _DERIVED
