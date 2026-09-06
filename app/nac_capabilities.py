"""I10 — provider capability and consent readiness.

Reads the authored `docs/nac_capabilities.json` manifest (built from H2's own
recorded evidence captures, never generated at request time) and answers
"is this ready" purely from local state: the manifest's own recorded status
plus whatever the caller's own request already contains. `preflight()` never
contacts a provider — it only tells a caller whether their own call would be
answerable at all, mirroring P1's zero-SDK-call missing-claim guarantee
rather than adding a second copy of it inside the real provider path.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.schemas import VerificationRequest

CAPABILITIES_PATH = Path(__file__).parent.parent / "docs" / "nac_capabilities.json"


def load_capabilities() -> dict:
    return json.loads(CAPABILITIES_PATH.read_text(encoding="utf-8"))


def capability_for(action: str) -> dict | None:
    for capability in load_capabilities()["capabilities"]:
        if capability["action"] == action:
            return capability
    return None


def preflight(action: str, request: VerificationRequest) -> dict:
    """Local-only readiness: {"ready": bool, "reason": str | None}."""
    capability = capability_for(action)
    if capability is None:
        return {"ready": False, "reason": f"no capability record for {action!r}"}
    if capability["status"] == "unavailable":
        return {"ready": False, "reason": capability["coverage_caveat"]}
    if action == "location_verify" and request.context.claimed_location is None:
        return {
            "ready": False,
            "reason": "no claimed_location on the request; Location Verification answers a claim",
        }
    return {"ready": True, "reason": None}
