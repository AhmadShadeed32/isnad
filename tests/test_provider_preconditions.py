"""P1 — the location-evidence provider boundary.

Neither provider may report a location-match verdict when the caller never
made a location claim. `RequestContext.claimed_location` is optional, and
"the merchant did not tell us where they claim to be" is not the same fact as
"the network checked and the device is there" — collapsing the two would be
exactly the fabricated-evidence bug this suite exists to catch.

Both providers must return the same normalized shape for the missing-claim
case: `Result.INFO` / `EVIDENCE_UNAVAILABLE`, wrapped in the ordinary
`EvidenceLink` contract (provenance, consent basis, source, window). NacProvider
additionally must never touch the live SDK when there is no claim to check.
"""

from __future__ import annotations

import pytest

from app.domain.enums import Action, Result
from app.domain.schemas import Area, RequestContext, VerificationRequest
from app.providers.mock import MockProvider
from app.providers.nac import NacProvider
from app.providers.vocabulary import detail_for

_CLAIM = Area(lat=31.9539, lon=35.9106, radius_m=2000)


# --------------------------- MockProvider ------------------------------------


@pytest.mark.asyncio
async def test_mock_location_with_no_claim_is_unavailable_not_a_fabricated_match():
    """This is the P1 bug: MockProvider used to return its scripted
    match/mismatch fixture even with no claim in the request at all."""
    request = VerificationRequest(
        phone_number="+962790000001",  # _CLEAN scenario: scripted AT_CLAIMED_LOCATION
        context=RequestContext(event="checkout"),
    )
    assert request.context.claimed_location is None

    link = await MockProvider().gather(Action.LOCATION_VERIFY, request)

    assert link.result == Result.INFO
    assert link.signal == "EVIDENCE_UNAVAILABLE"
    assert link.detail == detail_for("EVIDENCE_UNAVAILABLE")
    # The ordinary EvidenceLink contract must still be intact.
    assert link.source == "mock"
    assert link.consent_basis == "3-legged CIBA token"
    assert link.api  # non-empty API label


@pytest.mark.asyncio
async def test_mock_location_with_no_claim_is_unavailable_even_for_the_ghost_scenario():
    """The precondition applies before fixture selection, for every scenario —
    not just the clean one."""
    request = VerificationRequest(
        phone_number="+962790000002",  # _GHOST scenario: scripted NOT_AT_CLAIMED_LOCATION
        context=RequestContext(event="checkout"),
    )

    link = await MockProvider().gather(Action.LOCATION_VERIFY, request)

    assert link.result == Result.INFO
    assert link.signal == "EVIDENCE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_mock_location_with_a_claim_returns_the_scripted_match():
    request = VerificationRequest(
        phone_number="+962790000001",  # _CLEAN scenario
        context=RequestContext(event="checkout", claimed_location=_CLAIM),
    )

    link = await MockProvider().gather(Action.LOCATION_VERIFY, request)

    assert link.result == Result.PASS
    assert link.signal == "AT_CLAIMED_LOCATION"
    assert link.source == "mock"


@pytest.mark.asyncio
async def test_mock_location_with_a_claim_returns_the_scripted_mismatch():
    request = VerificationRequest(
        phone_number="+962790000002",  # _GHOST scenario
        context=RequestContext(event="checkout", claimed_location=_CLAIM),
    )

    link = await MockProvider().gather(Action.LOCATION_VERIFY, request)

    assert link.result == Result.FLAG
    assert link.signal == "NOT_AT_CLAIMED_LOCATION"


@pytest.mark.asyncio
async def test_mock_other_actions_are_unaffected_by_the_location_precondition():
    """The fix must be scoped to LOCATION_VERIFY only."""
    request = VerificationRequest(
        phone_number="+962790000001",
        context=RequestContext(event="checkout"),
    )
    link = await MockProvider().gather(Action.NUMBER_VERIFY, request)
    assert link.result == Result.PASS
    assert link.signal == "NUMBER_MATCH"


# ----------------------------- NacProvider ------------------------------------


class _Response:
    def __init__(self, **values):
        self.__dict__.update(values)


class _FakeLocationVerify:
    def __init__(self, verification_result: str = "TRUE"):
        self.calls: list[dict] = []
        self._result = verification_result

    def verify_v1(self, **kwargs):
        self.calls.append(kwargs)
        return _Response(verification_result=self._result)


class _FailingLocationVerify:
    def __init__(self):
        self.calls: list[dict] = []

    def verify_v1(self, **kwargs):
        self.calls.append(kwargs)
        raise RuntimeError("provider request failed")


class _FakeClient:
    def __init__(self, location):
        self.location = location


def _nac_provider(location) -> NacProvider:
    provider = object.__new__(NacProvider)
    provider.client = _FakeClient(location)
    provider.number_verification_token = None
    return provider


@pytest.mark.asyncio
async def test_nac_location_with_no_claim_is_unavailable_and_never_touches_the_sdk():
    fake_location = _FakeLocationVerify()
    provider = _nac_provider(fake_location)
    request = VerificationRequest(
        phone_number="+99999991000",
        context=RequestContext(event="checkout"),
    )
    assert request.context.claimed_location is None

    link = await provider.gather(Action.LOCATION_VERIFY, request)

    assert link.result == Result.INFO
    assert link.signal == "EVIDENCE_UNAVAILABLE"
    assert link.source == "nac"
    # The whole point: no claim means the live SDK is never called.
    assert fake_location.calls == []


@pytest.mark.asyncio
async def test_nac_location_with_a_claim_sends_the_exact_circle_and_radius():
    fake_location = _FakeLocationVerify(verification_result="TRUE")
    provider = _nac_provider(fake_location)
    request = VerificationRequest(
        phone_number="+99999991000",
        context=RequestContext(event="checkout", claimed_location=_CLAIM),
    )

    link = await provider.gather(Action.LOCATION_VERIFY, request)

    assert link.result == Result.PASS
    assert link.signal == "AT_CLAIMED_LOCATION"
    assert len(fake_location.calls) == 1
    call = fake_location.calls[0]
    assert call["device"] == {"phone_number": "+99999991000"}
    assert call["area"] == {
        "area_type": "CIRCLE",
        "center": {"latitude": _CLAIM.lat, "longitude": _CLAIM.lon},
        "radius": _CLAIM.radius_m,
    }


@pytest.mark.asyncio
async def test_nac_location_mismatch_with_a_claim():
    fake_location = _FakeLocationVerify(verification_result="FALSE")
    provider = _nac_provider(fake_location)
    request = VerificationRequest(
        phone_number="+99999991000",
        context=RequestContext(event="checkout", claimed_location=_CLAIM),
    )

    link = await provider.gather(Action.LOCATION_VERIFY, request)

    assert link.result == Result.FLAG
    assert link.signal == "NOT_AT_CLAIMED_LOCATION"
    assert len(fake_location.calls) == 1


@pytest.mark.asyncio
async def test_nac_location_provider_failure_with_a_claim_is_unavailable_not_a_crash():
    fake_location = _FailingLocationVerify()
    provider = _nac_provider(fake_location)
    request = VerificationRequest(
        phone_number="+99999991000",
        context=RequestContext(event="checkout", claimed_location=_CLAIM),
    )

    link = await provider.gather(Action.LOCATION_VERIFY, request)

    assert link.result == Result.INFO
    assert link.signal == "PROVIDER_UNAVAILABLE"
    assert link.source == "nac"
    assert len(fake_location.calls) == 1  # the call was attempted, then failed
