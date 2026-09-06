"""Offline fake mobile-operator OIDC server for the Number Verification
consent journey (P4a).

This is fixture infrastructure, not a claim about Nokia's or any operator's
actual authorization screen. It exists so app/providers/fake_nac.py can drive
the real OIDC contract (state, nonce, prompt=none, an id_token that carries
the nonce, single-use code, Basic client auth) end to end with no network
call and no vendor credentials — see app/providers/oidc_flow.py and
app/oidc.py, which this app's tokens are validated against, unmodified.

Two departures from what a real operator does, both deliberate and both
documented here rather than left to be discovered:

1. `prompt=none` on the real contract means network-based, non-interactive
   authentication — there is no consent screen. This fake still renders one,
   because *some* way to drive a decision is needed for a browser journey and
   for local development; it is a testing convenience, not a faithful
   reproduction of silent authentication.
2. The approval screen lets the tester choose NUMBER_MATCH, NUMBER_MISMATCH,
   or denial. A real subscriber never gets to pick their own verification
   result — that choice exists here only to exercise Isnad's three outcomes
   without a second operator account.

Run with: uvicorn demo.fake_operator.app:app --port 8801
"""

from __future__ import annotations

import base64
import html
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Form, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jwt.algorithms import RSAAlgorithm

from app.providers.fake_nac import FAKE_CLIENT_ID, FAKE_CLIENT_SECRET

app = FastAPI(title="Isnad fake operator (offline, P4a)")

# Generated fresh per process. Every id_token this process issues verifies
# only against this run's own /jwks.json — restarting invalidates any
# in-flight consent, same as rotating a real signing key would.
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_KID = "fake-operator-key-1"
_ID_TOKEN_TTL_SECONDS = 300


@dataclass
class _AuthCode:
    client_id: str
    redirect_uri: str
    nonce: str
    login_hint: str
    match: bool
    used: bool = False


@dataclass
class _AccessToken:
    login_hint: str
    match: bool


# Process-local, unbounded-but-tiny: this app only ever serves one interactive
# operator session in local development or a test run, never a real deployment.
_codes: dict[str, _AuthCode] = {}
_tokens: dict[str, _AccessToken] = {}


def _issuer(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@app.get("/.well-known/openid-configuration")
async def discovery(request: Request) -> dict:
    issuer = _issuer(request)
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/authorize",
        "token_endpoint": f"{issuer}/token",
        "jwks_uri": f"{issuer}/jwks.json",
    }


@app.get("/jwks.json")
async def jwks() -> dict:
    jwk = RSAAlgorithm.to_jwk(_PRIVATE_KEY.public_key(), as_dict=True)
    jwk["kid"] = _KID
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return {"keys": [jwk]}


@app.get("/authorize", response_class=HTMLResponse)
async def authorize(
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(...),
    state: str = Query(..., max_length=256),
    nonce: str = Query(..., max_length=256),
    login_hint: str = Query(..., max_length=32),
    prompt: str | None = Query(default=None),
) -> HTMLResponse:
    if response_type != "code":
        raise HTTPException(status_code=400, detail="response_type must be 'code'")

    def esc(value: str) -> str:
        return html.escape(value, quote=True)

    hidden_fields = "".join(
        f'<input type="hidden" name="{name}" value="{esc(value)}">'
        for name, value in (
            ("client_id", client_id),
            ("redirect_uri", redirect_uri),
            ("state", state),
            ("nonce", nonce),
            ("login_hint", login_hint),
        )
    )
    return HTMLResponse(f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Fake operator — Number Verification</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 3rem auto; padding: 0 1rem; }}
p.notice {{ background: #fff3cd; border: 1px solid #d9c27a; padding: 0.75rem; border-radius: 6px; }}
button {{ display: block; width: 100%; margin: 0.5rem 0; padding: 0.75rem; font-size: 1rem; border-radius: 6px; border: 1px solid #ccc; cursor: pointer; }}
button.match {{ background: #1a7f37; color: white; border-color: #1a7f37; }}
button.mismatch {{ background: #b35900; color: white; border-color: #b35900; }}
button.deny {{ background: #b91c1c; color: white; border-color: #b91c1c; }}
code {{ word-break: break-all; }}
</style></head>
<body>
<p class="notice">This is an <strong>offline fake operator</strong>, not a real network.
On a real mobile connection this step never shows a screen (prompt=none is
network-based, silent authentication) — this page exists only so a developer
can drive the three outcomes locally.</p>
<p>Number Verification requested for <code>{esc(login_hint)}</code> by
<code>{esc(client_id)}</code>.</p>
<form method="post" action="/authorize/decide">
{hidden_fields}
<button class="match" type="submit" name="decision" value="approve_match">
Approve — this is my number
</button>
<button class="mismatch" type="submit" name="decision" value="approve_mismatch">
Approve — but I'm signed in with a different number
</button>
<button class="deny" type="submit" name="decision" value="deny">Deny</button>
</form>
</body></html>""")


@app.post("/authorize/decide")
async def authorize_decide(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    state: str = Form(...),
    nonce: str = Form(...),
    login_hint: str = Form(...),
    decision: str = Form(...),
) -> RedirectResponse:
    if decision == "deny":
        query = urlencode({"error": "access_denied", "state": state})
        return RedirectResponse(f"{redirect_uri}?{query}", status_code=303)
    if decision not in {"approve_match", "approve_mismatch"}:
        raise HTTPException(status_code=400, detail="unknown decision")

    code = secrets.token_urlsafe(24)
    _codes[code] = _AuthCode(
        client_id=client_id,
        redirect_uri=redirect_uri,
        nonce=nonce,
        login_hint=login_hint,
        match=decision == "approve_match",
    )
    query = urlencode({"code": code, "state": state})
    return RedirectResponse(f"{redirect_uri}?{query}", status_code=303)


@app.post("/token")
async def token(
    request: Request,
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="unsupported grant_type")
    if not authorization or not authorization.startswith("Basic "):
        raise HTTPException(status_code=401, detail="client authentication required")
    try:
        decoded = base64.b64decode(authorization[len("Basic ") :]).decode("utf-8")
        client_id, _, client_secret = decoded.partition(":")
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=401, detail="malformed client authentication") from exc
    if not secrets.compare_digest(client_id, FAKE_CLIENT_ID) or not secrets.compare_digest(
        client_secret, FAKE_CLIENT_SECRET
    ):
        raise HTTPException(status_code=401, detail="invalid client credentials")

    auth_code = _codes.get(code)
    if auth_code is None or auth_code.used:
        raise HTTPException(status_code=400, detail="invalid_grant")
    if auth_code.redirect_uri != redirect_uri or auth_code.client_id != client_id:
        raise HTTPException(status_code=400, detail="invalid_grant")
    auth_code.used = True  # single-use, mirrors ConsentStore's own state handling

    access_token = secrets.token_urlsafe(32)
    _tokens[access_token] = _AccessToken(login_hint=auth_code.login_hint, match=auth_code.match)

    now = int(time.time())
    claims = {
        "iss": _issuer(request),
        "aud": client_id,
        "sub": auth_code.login_hint,
        "iat": now,
        "exp": now + _ID_TOKEN_TTL_SECONDS,
        "nonce": auth_code.nonce,
    }
    id_token = jwt.encode(claims, _PRIVATE_KEY, algorithm="RS256", headers={"kid": _KID})
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": _ID_TOKEN_TTL_SECONDS,
            "id_token": id_token,
        }
    )


@app.post("/verify")
async def verify(request: Request, authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="bearer token required")
    access_token = authorization[len("Bearer ") :]
    record = _tokens.get(access_token)
    if record is None:
        raise HTTPException(status_code=401, detail="invalid or expired access token")

    body = await request.json()
    phone_number = body.get("phoneNumber") if isinstance(body, dict) else None
    verified = record.match and phone_number == record.login_hint
    return {"devicePhoneNumberVerified": verified}
