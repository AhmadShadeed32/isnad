"""P4a — the offline fake operator and FakeNacProvider, end to end.

Runs entirely over httpx.ASGITransport: no real socket, no vendor SDK, no
network. FakeNacProvider drives the exact same oidc_flow/oidc validation
NacProvider's manual path uses (tests/test_nac_provider.py exercises that
path directly against a hand-built JWKS); this file is the "does the whole
offline contract actually round-trip" check the handoff asks for.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

import app.providers.fake_nac as fake_nac_module
from app.config import makes_billable_calls, settings
from app.domain.enums import Action, Result
from app.domain.schemas import VerificationRequest
from app.providers.fake_nac import FAKE_CLIENT_ID, FakeNacProvider
from demo.fake_operator.app import app as fake_app

BASE_URL = "https://fake-operator.test"
REDIRECT_URI = "https://merchant.test/callback"

# `fake_nac_module.httpx` is the same shared `httpx` module object this file
# imports, so patching an attribute on it mutates `httpx.AsyncClient` globally
# for the duration of the test. Capture the real class once, before any
# patching, so the operator-side test client below still gets an unpatched one.
_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _patch_to_asgi(monkeypatch) -> None:
    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        return _REAL_ASYNC_CLIENT(
            transport=httpx.ASGITransport(app=fake_app), base_url=BASE_URL, **kwargs
        )

    monkeypatch.setattr(fake_nac_module.httpx, "AsyncClient", factory)
    monkeypatch.setattr(settings, "nac_fake_base_url", BASE_URL)


async def _operator_client() -> httpx.AsyncClient:
    return _REAL_ASYNC_CLIENT(transport=httpx.ASGITransport(app=fake_app), base_url=BASE_URL)


def _query(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


async def _decide(client: httpx.AsyncClient, auth_query: dict[str, str], decision: str) -> str:
    """Submit the operator's decision and return the redirected callback URL."""
    response = await client.post(
        "/authorize/decide",
        data={
            "client_id": auth_query["client_id"],
            "redirect_uri": auth_query["redirect_uri"],
            "state": auth_query["state"],
            "nonce": auth_query["nonce"],
            "login_hint": auth_query["login_hint"],
            "decision": decision,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response.headers["location"]


@pytest.mark.asyncio
async def test_the_authorization_url_carries_state_nonce_and_prompt_none(monkeypatch):
    _patch_to_asgi(monkeypatch)
    provider = FakeNacProvider()

    url = await provider.begin_number_verification(
        "+99999991000", REDIRECT_URI, "state-1", "nonce-1"
    )

    query = _query(url)
    assert query["client_id"] == FAKE_CLIENT_ID
    assert query["state"] == "state-1"
    assert query["nonce"] == "nonce-1"
    assert query["prompt"] == "none"
    assert query["login_hint"] == "+99999991000"


@pytest.mark.asyncio
async def test_a_full_journey_ending_in_number_match(monkeypatch):
    _patch_to_asgi(monkeypatch)
    provider = FakeNacProvider()

    url = await provider.begin_number_verification(
        "+99999991000", REDIRECT_URI, "state-1", "nonce-1"
    )
    async with await _operator_client() as client:
        callback_url = await _decide(client, _query(url), "approve_match")

    code = _query(callback_url)["code"]
    access_token = await provider.exchange_number_verification_code(
        code, REDIRECT_URI, "nonce-1"
    )
    provider.number_verification_token = access_token
    link = await provider.gather(
        Action.NUMBER_VERIFY, VerificationRequest(phone_number="+99999991000")
    )

    assert link.result == Result.PASS
    assert link.signal == "NUMBER_MATCH"
    assert link.source == "nac_fake"


@pytest.mark.asyncio
async def test_a_full_journey_ending_in_number_mismatch(monkeypatch):
    _patch_to_asgi(monkeypatch)
    provider = FakeNacProvider()

    url = await provider.begin_number_verification(
        "+99999991000", REDIRECT_URI, "state-2", "nonce-2"
    )
    async with await _operator_client() as client:
        callback_url = await _decide(client, _query(url), "approve_mismatch")

    code = _query(callback_url)["code"]
    access_token = await provider.exchange_number_verification_code(
        code, REDIRECT_URI, "nonce-2"
    )
    provider.number_verification_token = access_token
    link = await provider.gather(
        Action.NUMBER_VERIFY, VerificationRequest(phone_number="+99999991000")
    )

    assert link.result == Result.FLAG
    assert link.signal == "NUMBER_MISMATCH"


@pytest.mark.asyncio
async def test_a_denied_authorization_never_yields_a_code(monkeypatch):
    _patch_to_asgi(monkeypatch)
    provider = FakeNacProvider()

    url = await provider.begin_number_verification(
        "+99999991000", REDIRECT_URI, "state-3", "nonce-3"
    )
    async with await _operator_client() as client:
        callback_url = await _decide(client, _query(url), "deny")

    callback_query = _query(callback_url)
    assert callback_query["error"] == "access_denied"
    assert "code" not in callback_query


@pytest.mark.asyncio
async def test_an_authorization_code_is_single_use(monkeypatch):
    _patch_to_asgi(monkeypatch)
    provider = FakeNacProvider()

    url = await provider.begin_number_verification(
        "+99999991000", REDIRECT_URI, "state-4", "nonce-4"
    )
    async with await _operator_client() as client:
        callback_url = await _decide(client, _query(url), "approve_match")
    code = _query(callback_url)["code"]

    await provider.exchange_number_verification_code(code, REDIRECT_URI, "nonce-4")

    with pytest.raises(RuntimeError):
        await provider.exchange_number_verification_code(code, REDIRECT_URI, "nonce-4")


@pytest.mark.asyncio
async def test_exchange_rejects_wrong_client_credentials(monkeypatch):
    _patch_to_asgi(monkeypatch)
    monkeypatch.setattr(fake_nac_module, "FAKE_CLIENT_SECRET", "not-the-real-secret")
    provider = FakeNacProvider()

    url = await provider.begin_number_verification(
        "+99999991000", REDIRECT_URI, "state-5", "nonce-5"
    )
    async with await _operator_client() as client:
        callback_url = await _decide(client, _query(url), "approve_match")
    code = _query(callback_url)["code"]

    with pytest.raises(RuntimeError):
        await provider.exchange_number_verification_code(code, REDIRECT_URI, "nonce-5")


@pytest.mark.asyncio
async def test_gather_reports_every_other_action_as_unavailable(monkeypatch):
    _patch_to_asgi(monkeypatch)
    provider = FakeNacProvider()

    link = await provider.gather(
        Action.SIM_SWAP, VerificationRequest(phone_number="+99999991000")
    )

    assert link.result == Result.INFO
    assert link.signal == "EVIDENCE_UNAVAILABLE"
    assert link.source == "nac_fake"


@pytest.mark.asyncio
async def test_gather_without_a_token_reports_consent_required(monkeypatch):
    _patch_to_asgi(monkeypatch)
    provider = FakeNacProvider()

    link = await provider.gather(
        Action.NUMBER_VERIFY, VerificationRequest(phone_number="+99999991000")
    )

    assert link.signal == "CONSENT_REQUIRED"
    assert link.requires_consent is True


def test_the_fake_provider_never_makes_a_billable_call():
    original = settings.provider
    try:
        settings.provider = "nac_fake"
        assert makes_billable_calls(settings) is False
    finally:
        settings.provider = original
