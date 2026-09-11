"""Unit tests for app/oidc.py's id_token validation (P4a).

A real RSA key pair signs each token; a hand-built JWKS document is served
through httpx.MockTransport, so these run fully offline with no real socket
and no dependency on demo/fake_operator.
"""

from __future__ import annotations

import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.oidc import IdTokenError, validate_id_token

ISSUER = "https://fake-operator.test"
AUDIENCE = "test-client-id"
NONCE = "the-authorization-request-nonce"
JWKS_URI = "https://fake-operator.test/jwks.json"

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_KID = "test-key-1"


def _jwk() -> dict:
    jwk = RSAAlgorithm.to_jwk(_PRIVATE_KEY.public_key(), as_dict=True)
    jwk["kid"] = _KID
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return jwk


def _sign(claims: dict, *, kid: str | None = _KID) -> str:
    headers = {"kid": kid} if kid else {}
    return jwt.encode(claims, _PRIVATE_KEY, algorithm="RS256", headers=headers)


def _claims(**overrides) -> dict:
    now = int(time.time())
    base = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "+99999991000",
        "iat": now,
        "exp": now + 300,
        "nonce": NONCE,
    }
    base.update(overrides)
    return base


def _client(jwks: dict | None = None, *, status_code: int = 200) -> httpx.AsyncClient:
    body = jwks if jwks is not None else {"keys": [_jwk()]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_a_valid_id_token_validates_and_returns_its_claims():
    token = _sign(_claims())
    async with _client() as client:
        claims = await validate_id_token(
            token,
            issuer=ISSUER,
            audience=AUDIENCE,
            nonce=NONCE,
            jwks_uri=JWKS_URI,
            http_client=client,
        )
    assert claims["sub"] == "+99999991000"


async def test_a_mismatched_nonce_is_rejected():
    token = _sign(_claims(nonce="attacker-supplied-nonce"))
    async with _client() as client:
        with pytest.raises(IdTokenError, match="nonce"):
            await validate_id_token(
                token,
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce=NONCE,
                jwks_uri=JWKS_URI,
                http_client=client,
            )


async def test_a_missing_nonce_claim_is_rejected():
    claims = _claims()
    del claims["nonce"]
    token = _sign(claims)
    async with _client() as client:
        with pytest.raises(IdTokenError, match="nonce"):
            await validate_id_token(
                token,
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce=NONCE,
                jwks_uri=JWKS_URI,
                http_client=client,
            )


async def test_a_wrong_audience_is_rejected():
    token = _sign(_claims(aud="someone-elses-client-id"))
    async with _client() as client:
        with pytest.raises(IdTokenError, match="validation"):
            await validate_id_token(
                token,
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce=NONCE,
                jwks_uri=JWKS_URI,
                http_client=client,
            )


async def test_a_wrong_issuer_is_rejected():
    token = _sign(_claims(iss="https://attacker.test"))
    async with _client() as client:
        with pytest.raises(IdTokenError, match="validation"):
            await validate_id_token(
                token,
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce=NONCE,
                jwks_uri=JWKS_URI,
                http_client=client,
            )


async def test_an_expired_token_is_rejected():
    now = int(time.time())
    token = _sign(_claims(iat=now - 3600, exp=now - 1800))
    async with _client() as client:
        with pytest.raises(IdTokenError, match="validation"):
            await validate_id_token(
                token,
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce=NONCE,
                jwks_uri=JWKS_URI,
                http_client=client,
            )


async def test_a_token_signed_by_a_different_key_is_rejected():
    """A forged token: right claims, wrong (attacker's own) signing key."""
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged = jwt.encode(_claims(), other_key, algorithm="RS256", headers={"kid": _KID})
    async with _client() as client:
        with pytest.raises(IdTokenError, match="validation"):
            await validate_id_token(
                forged,
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce=NONCE,
                jwks_uri=JWKS_URI,
                http_client=client,
            )


async def test_an_unknown_kid_is_rejected():
    token = _sign(_claims(), kid="not-in-the-jwks")
    async with _client() as client:
        with pytest.raises(IdTokenError, match="kid"):
            await validate_id_token(
                token,
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce=NONCE,
                jwks_uri=JWKS_URI,
                http_client=client,
            )


async def test_an_unsigned_none_algorithm_token_is_rejected():
    """The classic alg=none forgery must never reach signature verification."""
    token = jwt.encode(_claims(), key="", algorithm="none")
    async with _client() as client:
        with pytest.raises(IdTokenError, match="unsupported"):
            await validate_id_token(
                token,
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce=NONCE,
                jwks_uri=JWKS_URI,
                http_client=client,
            )


async def test_a_malformed_jwks_document_is_rejected():
    token = _sign(_claims())
    async with _client(jwks={"not_keys": []}) as client:
        with pytest.raises(IdTokenError, match="JWKS"):
            await validate_id_token(
                token,
                issuer=ISSUER,
                audience=AUDIENCE,
                nonce=NONCE,
                jwks_uri=JWKS_URI,
                http_client=client,
            )
