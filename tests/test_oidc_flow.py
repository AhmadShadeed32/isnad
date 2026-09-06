"""Unit tests for app/providers/oidc_flow.py (P4a shared manual OAuth flow)."""

from __future__ import annotations

import time
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.providers.oidc_flow import (
    OidcFlowError,
    build_authorization_url,
    complete_number_verification_exchange,
    exchange_code_for_tokens,
)

ISSUER = "https://fake-operator.test"
AUDIENCE = "test-client-id"
TOKEN_ENDPOINT = "https://fake-operator.test/token"
JWKS_URI = "https://fake-operator.test/jwks.json"
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_KID = "flow-test-key"


def _id_token(nonce: str) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "+99999991000",
        "iat": now,
        "exp": now + 300,
        "nonce": nonce,
    }
    return jwt.encode(claims, _PRIVATE_KEY, algorithm="RS256", headers={"kid": _KID})


def test_build_authorization_url_carries_state_nonce_and_prompt_none():
    url = build_authorization_url(
        authorization_endpoint="https://operator.test/authorize",
        client_id="client-1",
        redirect_uri="https://merchant.test/callback",
        scope="dpv:FraudPreventionAndDetection number-verification:verify",
        state="the-state",
        nonce="the-nonce",
        login_hint="+99999991000",
    )
    query = parse_qs(urlsplit(url).query)
    assert query["state"] == ["the-state"]
    assert query["nonce"] == ["the-nonce"]
    assert query["prompt"] == ["none"]
    assert query["response_type"] == ["code"]
    assert query["login_hint"] == ["+99999991000"]


def test_build_authorization_url_rejects_non_https_by_default():
    with pytest.raises(OidcFlowError, match="HTTPS"):
        build_authorization_url(
            authorization_endpoint="http://operator.test/authorize",
            client_id="client-1",
            redirect_uri="https://merchant.test/callback",
            scope="scope",
            state="s",
            nonce="n",
            login_hint="+99999991000",
        )


async def test_exchange_code_for_tokens_sends_client_secret_as_basic_auth():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth_header"] = request.headers.get("authorization")
        seen["body"] = dict(parse_qs(request.content.decode()))
        return httpx.Response(200, json={"access_token": "at", "id_token": "it"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        body = await exchange_code_for_tokens(
            http_client=client,
            token_endpoint=TOKEN_ENDPOINT,
            client_id="client-1",
            client_secret="shh",
            code="the-code",
            redirect_uri="https://merchant.test/callback",
        )
    assert body == {"access_token": "at", "id_token": "it"}
    assert seen["auth_header"].startswith("Basic ")
    # client_id travels in the Basic-auth credential, not doubled into the body.
    assert "client_id" not in seen["body"]
    assert seen["body"]["code"] == ["the-code"]


async def test_exchange_raises_a_flow_error_on_a_provider_http_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(OidcFlowError, match="token exchange failed"):
            await exchange_code_for_tokens(
                http_client=client,
                token_endpoint=TOKEN_ENDPOINT,
                client_id="client-1",
                client_secret=None,
                code="bad-code",
                redirect_uri="https://merchant.test/callback",
            )


async def test_complete_exchange_succeeds_and_returns_the_access_token():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            return httpx.Response(
                200, json={"access_token": "at-123", "id_token": _id_token("the-nonce")}
            )
        if request.url.path == "/jwks.json":
            jwk = RSAAlgorithm.to_jwk(_PRIVATE_KEY.public_key(), as_dict=True)
            jwk["kid"] = _KID
            return httpx.Response(200, json={"keys": [jwk]})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        access_token = await complete_number_verification_exchange(
            http_client=client,
            token_endpoint=TOKEN_ENDPOINT,
            client_id=AUDIENCE,
            client_secret="shh",
            code="the-code",
            redirect_uri="https://merchant.test/callback",
            issuer=ISSUER,
            audience=AUDIENCE,
            nonce="the-nonce",
            jwks_uri=JWKS_URI,
        )
    assert access_token == "at-123"


async def test_complete_exchange_fails_closed_when_the_id_token_is_missing():
    """The documented contract always returns an id_token; a bare access-token
    response must not be silently accepted as compatible (handoff §3 P4a.1)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"access_token": "at-only"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(OidcFlowError, match="id_token"):
            await complete_number_verification_exchange(
                http_client=client,
                token_endpoint=TOKEN_ENDPOINT,
                client_id=AUDIENCE,
                client_secret="shh",
                code="the-code",
                redirect_uri="https://merchant.test/callback",
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce="the-nonce",
                jwks_uri=JWKS_URI,
            )


async def test_complete_exchange_fails_closed_when_the_access_token_is_missing():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id_token": _id_token("the-nonce")})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(OidcFlowError, match="access_token"):
            await complete_number_verification_exchange(
                http_client=client,
                token_endpoint=TOKEN_ENDPOINT,
                client_id=AUDIENCE,
                client_secret="shh",
                code="the-code",
                redirect_uri="https://merchant.test/callback",
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce="the-nonce",
                jwks_uri=JWKS_URI,
            )


async def test_complete_exchange_rejects_a_replayed_nonce():
    """The id_token's nonce belongs to a different, earlier authorization request."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            return httpx.Response(
                200, json={"access_token": "at-123", "id_token": _id_token("stale-nonce")}
            )
        jwk = RSAAlgorithm.to_jwk(_PRIVATE_KEY.public_key(), as_dict=True)
        jwk["kid"] = _KID
        return httpx.Response(200, json={"keys": [jwk]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(Exception, match="nonce"):
            await complete_number_verification_exchange(
                http_client=client,
                token_endpoint=TOKEN_ENDPOINT,
                client_id=AUDIENCE,
                client_secret="shh",
                code="the-code",
                redirect_uri="https://merchant.test/callback",
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce="the-current-nonce",
                jwks_uri=JWKS_URI,
            )
