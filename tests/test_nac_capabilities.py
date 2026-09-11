"""I10 — provider capability and consent readiness.

Local-only: preflight() never contacts a provider. It only reads the
authored capabilities manifest and inspects the request already in hand,
mirroring P1's own zero-SDK-call missing-claim guarantee rather than
duplicating a second copy of it.
"""

from __future__ import annotations

from app.domain.schemas import Area, RequestContext, VerificationRequest
from app.nac_capabilities import capability_for, load_capabilities, preflight

LOCATION = Area(lat=31.9539, lon=35.9106, radius_m=2000)


def test_the_manifest_loads_and_every_source_reference_exists():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    data = load_capabilities()
    assert data["schema_version"] == 1
    assert len(data["capabilities"]) >= 6
    for cap in data["capabilities"]:
        assert (repo_root / cap["source_reference"]).exists()
        assert cap["status"] in {"verified", "unverified", "unavailable"}


def test_capability_for_a_known_action():
    cap = capability_for("number_verify")
    assert cap is not None
    assert cap["consent_required"] is True


def test_capability_for_an_unknown_action_is_none():
    assert capability_for("not_a_real_action") is None


def test_location_verify_without_a_claim_is_not_ready():
    request = VerificationRequest(
        phone_number="+962790000001", context=RequestContext(event="checkout")
    )
    result = preflight("location_verify", request)
    assert result["ready"] is False
    assert "claimed_location" in result["reason"]


def test_location_verify_with_a_claim_is_ready():
    request = VerificationRequest(
        phone_number="+962790000001",
        context=RequestContext(event="checkout", claimed_location=LOCATION),
    )
    result = preflight("location_verify", request)
    assert result["ready"] is True


def test_an_unavailable_capability_is_never_ready():
    request = VerificationRequest(
        phone_number="+962790000001", context=RequestContext(event="checkout")
    )
    result = preflight("device_intelligence", request)
    assert result["ready"] is False


def test_an_unknown_action_is_not_ready():
    request = VerificationRequest(
        phone_number="+962790000001", context=RequestContext(event="checkout")
    )
    result = preflight("not_a_real_action", request)
    assert result["ready"] is False
