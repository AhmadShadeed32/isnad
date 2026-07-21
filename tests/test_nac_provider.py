from __future__ import annotations

import pytest

from app.domain.enums import Action, Result
from app.domain.schemas import RequestContext, VerificationRequest
from app.providers.nac import NacProvider


class Response:
    def __init__(self, **values):
        self.__dict__.update(values)


class FakeSimSwap:
    def check(self, **kwargs):
        assert kwargs["phone_number"] == "+99999991000"
        return Response(swapped=True)


class FakeReachability:
    def retrieve_reachability_status(self, **kwargs):
        assert kwargs["device"] == {"phone_number": "+99999991000"}
        return Response(reachable=True, connectivity=["DATA", "SMS"])


class FakeDeviceStatus:
    def __init__(self):
        self.retrieve_reachability_status = FakeReachability().retrieve_reachability_status


class FakeClient:
    def __init__(self):
        self.sim_swap = FakeSimSwap()
        self.device_status = FakeDeviceStatus()


def _provider() -> NacProvider:
    provider = object.__new__(NacProvider)
    provider.client = FakeClient()
    provider.number_verification_token = None
    return provider


@pytest.mark.asyncio
async def test_nac_provider_normalizes_sim_swap():
    link = await _provider().gather(
        Action.SIM_SWAP,
        VerificationRequest(
            phone_number="+99999991000",
            context=RequestContext(event="checkout"),
        ),
    )

    assert link.source == "nac"
    assert link.result == Result.FLAG
    assert link.signal == "SIM_SWAPPED"
    assert "recent SIM swap" in link.detail


@pytest.mark.asyncio
async def test_nac_provider_normalizes_reachability():
    link = await _provider().gather(
        Action.REACHABILITY,
        VerificationRequest(phone_number="+99999991000"),
    )

    assert link.result == Result.PASS
    assert link.signal == "REACHABLE_NORMAL"
    assert "DATA, SMS" in link.detail


@pytest.mark.asyncio
async def test_nac_provider_does_not_fake_number_verification():
    link = await _provider().gather(
        Action.NUMBER_VERIFY,
        VerificationRequest(phone_number="+99999991000"),
    )

    assert link.result == Result.INFO
    assert link.signal == "CONSENT_REQUIRED"


class FakeNumberVerification:
    def get_oidc_url(self, **kwargs):
        assert kwargs["redirect_uri"] == "https://merchant.test/callback"
        assert kwargs["state"] == "state-123"
        assert kwargs["login_hint"] == "+99999991000"
        return "https://consent.test/authorize?state=state-123"

    def exchange_code_for_token(self, code, redirect_uri):
        assert code == "operator-code"
        assert redirect_uri == "https://merchant.test/callback"
        return "one-time-access-token"

    def verify(self, token, **kwargs):
        assert token == "one-time-access-token"
        assert kwargs["phone_number"] == "+99999991000"
        return {"device_phone_number_verified": True}


def _consent_provider() -> NacProvider:
    provider = _provider()
    provider.client.number_verification = FakeNumberVerification()
    return provider


@pytest.mark.asyncio
async def test_nac_provider_starts_and_completes_number_consent():
    provider = _consent_provider()

    url = await provider.begin_number_verification(
        "+99999991000", "https://merchant.test/callback", "state-123"
    )
    token = await provider.exchange_number_verification_code(
        "operator-code", "https://merchant.test/callback"
    )
    provider.number_verification_token = token
    link = await provider.gather(Action.NUMBER_VERIFY, VerificationRequest(phone_number="+99999991000"))

    assert url.endswith("state-123")
    assert token == "one-time-access-token"
    assert link.result == Result.PASS
    assert link.signal == "NUMBER_MATCH"
