"""Shared manual OIDC flow for Number Verification (P4a).

Both NacProvider's non-SDK fallback and the offline FakeNacProvider build the
authorization URL and exchange the code the same way, through this module —
so the fake operator exercises the identical contract and validation path a
real deployment would, rather than a parallel implementation that could drift
from it silently.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.oidc import validate_id_token


class OidcFlowError(RuntimeError):
    """The authorization or token endpoint did not honor the documented contract."""


def build_authorization_url(
    *,
    authorization_endpoint: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    nonce: str,
    login_hint: str,
    require_https: bool = True,
) -> str:
    """Build the Number Verification authorization URL.

    Always includes both `state` (CSRF) and `nonce` (replay protection via the
    returned id_token) and `prompt=none`, per the documented V1 contract:
    network-based authentication on a mobile connection does not show an
    interactive screen. The offline fake operator still renders one — that is
    a testing shim, not a claim about live behavior; see demo/fake_operator.
    """
    if require_https and not authorization_endpoint.lower().startswith("https://"):
        raise OidcFlowError("authorization endpoint must be HTTPS")
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "nonce": nonce,
            "prompt": "none",
            "login_hint": login_hint,
        }
    )
    separator = "&" if "?" in authorization_endpoint else "?"
    return f"{authorization_endpoint}{separator}{query}"


async def exchange_code_for_tokens(
    *,
    http_client: httpx.AsyncClient,
    token_endpoint: str,
    client_id: str,
    client_secret: str | None,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
    }
    auth = None
    if client_secret:
        auth = (client_id, client_secret)
        data.pop("client_id")
    try:
        response = await http_client.post(token_endpoint, data=data, auth=auth)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OidcFlowError("Number Verification token exchange failed") from exc
    body = response.json()
    if not isinstance(body, dict):
        raise OidcFlowError("token endpoint did not return a JSON object")
    return body


async def complete_number_verification_exchange(
    *,
    http_client: httpx.AsyncClient,
    token_endpoint: str,
    client_id: str,
    client_secret: str | None,
    code: str,
    redirect_uri: str,
    issuer: str,
    audience: str,
    nonce: str,
    jwks_uri: str,
    leeway_seconds: int = 60,
) -> str:
    """Exchange the code, validate the id_token, and return the access_token.

    Fails closed on a missing id_token: the documented contract returns one,
    and treating its absence as "compatible anyway" is exactly the assumption
    the handoff calls out as unaddressed. See the local consent journey notes.
    """
    token_response = await exchange_code_for_tokens(
        http_client=http_client,
        token_endpoint=token_endpoint,
        client_id=client_id,
        client_secret=client_secret,
        code=code,
        redirect_uri=redirect_uri,
    )
    access_token = token_response.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise OidcFlowError("token endpoint returned no access_token")
    id_token = token_response.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise OidcFlowError(
            "token endpoint returned no id_token; the documented contract requires "
            "one to validate the authorization request's nonce"
        )
    await validate_id_token(
        id_token,
        issuer=issuer,
        audience=audience,
        nonce=nonce,
        jwks_uri=jwks_uri,
        http_client=http_client,
        leeway_seconds=leeway_seconds,
    )
    return access_token
