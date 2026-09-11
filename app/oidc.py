"""ID-token validation shared by every OIDC-based Number Verification path (P4a).

The V1 documentation (networkascode.nokia.io, reviewed 6 Sep 2026) returns both
an access_token and an id_token from the token endpoint, and requires the nonce
sent in the authorization request to be validated as an id_token claim: "the
`nonce` you sent must appear as a claim in the id_token returned from the token
endpoint." This module is the one place that check happens, so both the real
provider's manual (non-SDK) exchange and the offline fake operator exercise
identical validation — a fake that skipped this would prove nothing about the
real contract.

JWKS is fetched with the caller's own httpx.AsyncClient rather than PyJWT's
built-in PyJWKClient (which uses urllib) so tests can inject an
httpx.ASGITransport bound directly to an in-process fake operator, with no real
socket involved.
"""

from __future__ import annotations

import hmac
import json
from typing import Any

import httpx
import jwt
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

_SUPPORTED_ALGORITHMS = {"RS256": RSAAlgorithm, "ES256": ECAlgorithm}


class IdTokenError(RuntimeError):
    """The id_token is missing, malformed, or fails contract validation.

    Deliberately a plain RuntimeError subclass: callers in app/providers/*
    already translate a bare RuntimeError into a 503 without echoing internal
    detail into an HTTP response.
    """


async def fetch_jwks(http_client: httpx.AsyncClient, jwks_uri: str) -> dict[str, Any]:
    response = await http_client.get(jwks_uri)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("keys"), list):
        raise IdTokenError("JWKS response has no usable 'keys' array")
    return body


def _select_key(jwks: dict[str, Any], kid: str | None) -> dict[str, Any]:
    keys = jwks.get("keys", [])
    if kid is not None:
        for key in keys:
            if key.get("kid") == kid:
                return key
        raise IdTokenError(f"no JWKS key matches id_token kid={kid!r}")
    if len(keys) == 1:
        return keys[0]
    raise IdTokenError("id_token has no kid and the JWKS has more than one key")


async def validate_id_token(
    id_token: str,
    *,
    issuer: str,
    audience: str,
    nonce: str,
    jwks_uri: str,
    http_client: httpx.AsyncClient,
    leeway_seconds: int = 60,
) -> dict[str, Any]:
    """Validate signature, iss, aud, exp/iat and nonce. Returns the claims.

    Fails closed: any missing or wrong field raises IdTokenError rather than
    returning a partial or best-effort result. There is no code path that
    treats an unverified decoded token as valid.
    """
    try:
        header = jwt.get_unverified_header(id_token)
    except jwt.PyJWTError as exc:
        raise IdTokenError("id_token header is malformed") from exc

    algorithm_name = header.get("alg")
    algorithm_cls = _SUPPORTED_ALGORITHMS.get(str(algorithm_name))
    if algorithm_cls is None:
        raise IdTokenError(f"unsupported id_token algorithm {algorithm_name!r}")

    jwks = await fetch_jwks(http_client, jwks_uri)
    jwk = _select_key(jwks, header.get("kid"))
    try:
        public_key = algorithm_cls.from_jwk(json.dumps(jwk))
    except (ValueError, TypeError, KeyError) as exc:
        raise IdTokenError("JWKS key could not be parsed") from exc

    try:
        claims = jwt.decode(
            id_token,
            key=public_key,
            algorithms=[algorithm_name],
            audience=audience,
            issuer=issuer,
            leeway=leeway_seconds,
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise IdTokenError(f"id_token failed validation: {exc}") from exc

    token_nonce = claims.get("nonce")
    if not isinstance(token_nonce, str) or not token_nonce:
        raise IdTokenError("id_token carries no nonce claim")
    if not hmac.compare_digest(token_nonce, nonce):
        raise IdTokenError("id_token nonce does not match the authorization request")

    return claims
