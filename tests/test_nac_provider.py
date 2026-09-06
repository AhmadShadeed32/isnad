from __future__ import annotations

import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

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
    # The window is the answer a boolean-against-max_age can give; a date is not.
    assert link.detail == "SIM swap inside the last 240 h"


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
        assert kwargs["nonce"] == "nonce-abc"
        assert kwargs["prompt"] == "none"
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
        "+99999991000", "https://merchant.test/callback", "state-123", "nonce-abc"
    )
    token = await provider.exchange_number_verification_code(
        "operator-code", "https://merchant.test/callback", "nonce-abc"
    )
    provider.number_verification_token = token
    link = await provider.gather(
        Action.NUMBER_VERIFY, VerificationRequest(phone_number="+99999991000")
    )

    assert url.endswith("state-123")
    assert token == "one-time-access-token"
    assert link.result == Result.PASS
    assert link.signal == "NUMBER_MATCH"


class FakeNumberVerificationRejectsNonce:
    """An SDK version whose get_oidc_url predates nonce/prompt support."""

    def get_oidc_url(self, **kwargs):
        if "nonce" in kwargs or "prompt" in kwargs:
            raise TypeError("get_oidc_url() got an unexpected keyword argument 'nonce'")
        return "https://consent.test/authorize?state=state-123"  # pragma: no cover


@pytest.mark.asyncio
async def test_begin_number_verification_falls_through_instead_of_dropping_nonce(monkeypatch):
    """The old code retried a TypeError with scope dropped. nonce/prompt must
    never be silently dropped the same way — that would ship a request the
    documented contract calls replay-vulnerable. It must fall through to the
    manual authorization-URL builder instead."""
    from app.config import settings

    provider = _provider()
    provider.client.number_verification = FakeNumberVerificationRejectsNonce()
    monkeypatch.setattr(settings, "nac_client_id", "manual-client-id")
    monkeypatch.setattr(settings, "nac_authorization_endpoint", "https://operator.test/authorize")

    url = await provider.begin_number_verification(
        "+99999991000", "https://merchant.test/callback", "state-123", "nonce-abc"
    )

    assert url.startswith("https://operator.test/authorize?")
    assert "nonce=nonce-abc" in url
    assert "prompt=none" in url
    assert "state=state-123" in url


class _ClientWithNoNumberVerificationApi:
    """The manual (non-SDK) exchange path used by the offline fake and by an
    installed SDK that has no number_verification/number_verify object."""


_MANUAL_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_MANUAL_KID = "manual-path-key"


def _manual_id_token(nonce: str, *, audience: str = "manual-client-id") -> str:
    now = int(time.time())
    claims = {
        "iss": "https://fake-operator.test",
        "aud": audience,
        "sub": "+99999991000",
        "iat": now,
        "exp": now + 300,
        "nonce": nonce,
    }
    return jwt.encode(claims, _MANUAL_KEY, algorithm="RS256", headers={"kid": _MANUAL_KID})


def _manual_provider(monkeypatch) -> NacProvider:
    from app.config import settings

    provider = object.__new__(NacProvider)
    provider.client = _ClientWithNoNumberVerificationApi()
    provider.number_verification_token = None
    monkeypatch.setattr(settings, "nac_client_id", "manual-client-id")
    monkeypatch.setattr(settings, "nac_client_secret", "manual-secret")
    monkeypatch.setattr(settings, "nac_token_endpoint", "https://fake-operator.test/token")
    monkeypatch.setattr(settings, "nac_issuer", "https://fake-operator.test")
    monkeypatch.setattr(settings, "nac_jwks_uri", "https://fake-operator.test/jwks.json")
    return provider


def _patch_httpx_to_mock_transport(monkeypatch, handler) -> None:
    import app.providers.nac as nac_module

    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        return real_async_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(nac_module.httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_manual_exchange_validates_the_id_token_and_returns_the_access_token(monkeypatch):
    provider = _manual_provider(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            return httpx.Response(
                200,
                json={"access_token": "manual-access-token", "id_token": _manual_id_token("n-1")},
            )
        jwk = RSAAlgorithm.to_jwk(_MANUAL_KEY.public_key(), as_dict=True)
        jwk["kid"] = _MANUAL_KID
        return httpx.Response(200, json={"keys": [jwk]})

    _patch_httpx_to_mock_transport(monkeypatch, handler)

    token = await provider.exchange_number_verification_code(
        "the-code", "https://merchant.test/callback", "n-1"
    )

    assert token == "manual-access-token"


@pytest.mark.asyncio
async def test_manual_exchange_fails_closed_on_a_replayed_nonce(monkeypatch):
    provider = _manual_provider(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "manual-access-token",
                    "id_token": _manual_id_token("stale-nonce-from-an-earlier-request"),
                },
            )
        jwk = RSAAlgorithm.to_jwk(_MANUAL_KEY.public_key(), as_dict=True)
        jwk["kid"] = _MANUAL_KID
        return httpx.Response(200, json={"keys": [jwk]})

    _patch_httpx_to_mock_transport(monkeypatch, handler)

    with pytest.raises(RuntimeError, match="nonce"):
        await provider.exchange_number_verification_code(
            "the-code", "https://merchant.test/callback", "the-current-nonce"
        )


@pytest.mark.asyncio
async def test_manual_exchange_fails_closed_when_the_id_token_is_absent(monkeypatch):
    provider = _manual_provider(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"access_token": "manual-access-token"})

    _patch_httpx_to_mock_transport(monkeypatch, handler)

    with pytest.raises(RuntimeError, match="id_token"):
        await provider.exchange_number_verification_code(
            "the-code", "https://merchant.test/callback", "n-1"
        )


@pytest.mark.asyncio
async def test_manual_exchange_requires_issuer_and_jwks_configuration(monkeypatch):
    from app.config import settings

    provider = _manual_provider(monkeypatch)
    monkeypatch.setattr(settings, "nac_issuer", None)

    with pytest.raises(RuntimeError, match="ISNAD_NAC_ISSUER"):
        await provider.exchange_number_verification_code(
            "the-code", "https://merchant.test/callback", "n-1"
        )
