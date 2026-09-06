"""Single-merchant reference harness for the live-consent journey (P4a).

A minimal operator-facing app that calls Isnad's existing consent API with
httpx, exactly as a real merchant backend would. It exists to give P4a (and
P3 after it) something to drive the consent journey through in a browser —
it is not a template for a production merchant integration, and it is
explicitly NOT a new SaaS identity system: one operator account, loopback by
default, in-memory state.

The browser never sees ISNAD_MERCHANT_API_KEY or a provider credential — only
this process talks to Isnad, over `httpx`, with the key read from the
environment. Bind this to loopback or a private network only; it has no TLS
of its own and is not hardened for the open internet.

Run with: uvicorn demo.merchant_pilot.app:app --port 8802
Required env: ISNAD_MERCHANT_API_KEY, PILOT_OPERATOR_USERNAME,
PILOT_OPERATOR_PASSWORD. Optional: ISNAD_BASE_URL (default
http://127.0.0.1:8000), PILOT_SESSION_TTL_SECONDS (default 1800).
"""

from __future__ import annotations

import ipaddress
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import segno
from fastapi import Cookie, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ValidationError

from app.domain.schemas import RequestContext

# --- configuration (env-only: this is a reference harness, not a config system) ---

ISNAD_BASE_URL = os.environ.get("ISNAD_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ISNAD_MERCHANT_API_KEY = os.environ.get("ISNAD_MERCHANT_API_KEY", "")
OPERATOR_USERNAME = os.environ.get("PILOT_OPERATOR_USERNAME", "")
OPERATOR_PASSWORD = os.environ.get("PILOT_OPERATOR_PASSWORD", "")
SESSION_TTL_SECONDS = int(os.environ.get("PILOT_SESSION_TTL_SECONDS", "1800"))
FLOW_RETENTION_SECONDS = int(os.environ.get("PILOT_FLOW_RETENTION_SECONDS", "3600"))
SESSION_COOKIE = "pilot_session"

if not ISNAD_MERCHANT_API_KEY or not OPERATOR_USERNAME or not OPERATOR_PASSWORD:
    raise RuntimeError(
        "ISNAD_MERCHANT_API_KEY, PILOT_OPERATOR_USERNAME and PILOT_OPERATOR_PASSWORD "
        "are all required to start the merchant pilot harness"
    )

_STATIC_DIR = Path(__file__).parent / "static"


def _now() -> datetime:
    return datetime.now(UTC)


# --- operator session store (synchronous, in-memory: one operator, one process) ---


@dataclass
class _Session:
    session_id: str
    csrf_token: str
    created_at: datetime
    expires_at: datetime


class SessionStore:
    def __init__(self, ttl_seconds: int) -> None:
        self._sessions: dict[str, _Session] = {}
        self._lock = threading.Lock()
        self.ttl_seconds = ttl_seconds

    def create(self) -> _Session:
        now = _now()
        session = _Session(
            session_id=secrets.token_urlsafe(32),
            csrf_token=secrets.token_urlsafe(32),
            created_at=now,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        with self._lock:
            self._sweep()
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str | None) -> _Session | None:
        if not session_id:
            return None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.expires_at <= _now():
                del self._sessions[session_id]
                return None
            return session

    def destroy(self, session_id: str | None) -> None:
        if not session_id:
            return
        with self._lock:
            self._sessions.pop(session_id, None)

    def _sweep(self) -> None:
        now = _now()
        for sid, session in list(self._sessions.items()):
            if session.expires_at <= now:
                del self._sessions[sid]


sessions = SessionStore(SESSION_TTL_SECONDS)


class LoginThrottle:
    """Bounded login attempts per source IP: a fixed window, not exponential
    backoff — this harness has one legitimate account, so simplicity wins."""

    def __init__(self, max_attempts: int = 8, window_seconds: int = 900) -> None:
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds

    def check(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            attempts = [t for t in self._failures.get(key, []) if now - t < self.window_seconds]
            self._failures[key] = attempts
            return len(attempts) < self.max_attempts

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._failures.setdefault(key, []).append(time.monotonic())

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_throttle = LoginThrottle()


# --- flow store (one flow = one merchant-initiated consent journey) ---


@dataclass
class FlowRecord:
    flow_id: str
    consent_id: str
    phone_number: str
    context_event: str
    authorization_url: str
    qr_svg: str
    created_at: datetime
    expires_at: datetime
    status: str = "PENDING"
    verifying: bool = False
    result: dict[str, Any] | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


class FlowStore:
    def __init__(self, retention_seconds: int) -> None:
        self._flows: dict[str, FlowRecord] = {}
        self._lock = threading.Lock()
        self.retention_seconds = retention_seconds

    def add(self, flow: FlowRecord) -> None:
        with self._lock:
            self._sweep()
            self._flows[flow.flow_id] = flow

    def get(self, flow_id: str) -> FlowRecord | None:
        with self._lock:
            return self._flows.get(flow_id)

    def _sweep(self) -> None:
        cutoff = _now() - timedelta(seconds=self.retention_seconds)
        for flow_id, flow in list(self._flows.items()):
            if flow.created_at <= cutoff:
                del self._flows[flow_id]


flows = FlowStore(FLOW_RETENTION_SECONDS)


# --- request validation ---

_PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


class NewFlowRequest(BaseModel):
    phone_number: str
    event: str = "checkout"
    account_age_days: int | None = None


# --- app ---

app = FastAPI(title="Isnad merchant pilot harness (P4a)")


def _client_is_private(request: Request) -> bool:
    host = request.client.host if request.client else ""
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return addr.is_loopback or addr.is_private


@app.middleware("http")
async def restrict_to_private_network(request: Request, call_next):
    """This harness has no TLS and one operator account: it must never be
    reachable from an arbitrary public address. Set PILOT_ALLOW_PUBLIC=true
    only behind a reverse proxy/VPN that already restricts access."""
    if os.environ.get("PILOT_ALLOW_PUBLIC", "").lower() != "true" and not _client_is_private(
        request
    ):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "this harness only accepts loopback/private connections"},
        )
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


def _require_session(pilot_session: str | None) -> _Session:
    session = sessions.get(pilot_session)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not logged in")
    return session


def _require_csrf(request: Request, session: _Session, csrf_header: str | None) -> None:
    origin = request.headers.get("origin")
    if origin is not None and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="cross-origin request")
    if not csrf_header or not secrets.compare_digest(csrf_header, session.csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="missing or bad CSRF token")


_LOGIN_PAGE = """<!doctype html>
<meta charset="utf-8">
<title>Merchant pilot — sign in</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:360px;margin:4rem auto}}
input{{display:block;width:100%;padding:.5rem;margin:.3rem 0 1rem;box-sizing:border-box}}
button{{width:100%;padding:.6rem;background:#1a7f37;color:#fff;border:0;border-radius:4px}}
.err{{color:#b91c1c}}
</style>
<form method="post" action="/login">
<h1>Merchant pilot</h1>
{error}
<label>Username<input type="text" name="username" autocomplete="username" required></label>
<label>Password<input type="password" name="password" autocomplete="current-password" required></label>
<button type="submit">Sign in</button>
</form>"""


@app.get("/login", response_class=HTMLResponse)
async def login_page() -> HTMLResponse:
    return HTMLResponse(_LOGIN_PAGE.format(error=""))


@app.post("/login")
async def login(request: Request) -> RedirectResponse:
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    client_key = request.client.host if request.client else "unknown"

    if not login_throttle.check(client_key):
        return HTMLResponse(
            _LOGIN_PAGE.format(
                error='<p class="err">Too many attempts. Try again later.</p>'
            ),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    valid = secrets.compare_digest(username, OPERATOR_USERNAME) and secrets.compare_digest(
        password, OPERATOR_PASSWORD
    )
    if not valid:
        login_throttle.record_failure(client_key)
        return HTMLResponse(
            _LOGIN_PAGE.format(error='<p class="err">Wrong username or password.</p>'),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    login_throttle.clear(client_key)
    session = sessions.create()
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE,
        session.session_id,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )
    return response


@app.post("/logout")
async def logout(pilot_session: str | None = Cookie(default=None)) -> RedirectResponse:
    sessions.destroy(pilot_session)
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard(pilot_session: str | None = Cookie(default=None)) -> HTMLResponse:
    session = sessions.get(pilot_session)
    if session is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("__CSRF_TOKEN__", session.csrf_token)
    return HTMLResponse(html)


@app.get("/flow/{flow_id}", response_class=HTMLResponse)
async def flow_page(flow_id: str, pilot_session: str | None = Cookie(default=None)) -> HTMLResponse:
    session = sessions.get(pilot_session)
    if session is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if flows.get(flow_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no such flow")
    html = (_STATIC_DIR / "flow.html").read_text(encoding="utf-8")
    html = html.replace("__FLOW_ID__", flow_id)
    return HTMLResponse(html)


def _with_viewbox(svg: str) -> str:
    match = re.search(r'width="(\d+)mm" height="(\d+)mm"', svg)
    if not match:
        return svg
    w, h = match.group(1), match.group(2)
    return svg.replace(match.group(0), f'{match.group(0)} viewBox="0 0 {w} {h}"', 1)


@app.post("/api/flows")
async def create_flow(
    request: Request,
    pilot_session: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
) -> dict:
    session = _require_session(pilot_session)
    _require_csrf(request, session, x_csrf_token)

    try:
        body = NewFlowRequest.model_validate(await request.json())
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())
    if not _PHONE_PATTERN.match(body.phone_number):
        raise HTTPException(status_code=422, detail="phone_number must be E.164")

    context = RequestContext(event=body.event, account_age_days=body.account_age_days)

    async with httpx.AsyncClient(base_url=ISNAD_BASE_URL, timeout=15.0) as client:
        response = await client.post(
            "/v1/consents/number-verification",
            headers={"Authorization": f"Bearer {ISNAD_MERCHANT_API_KEY}"},
            json={"phone_number": body.phone_number, "context": context.model_dump(mode="json")},
        )
    if response.status_code != status.HTTP_202_ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Isnad rejected the consent request",
        )
    payload = response.json()
    qr_svg = _with_viewbox(
        segno.make(payload["authorization_url"], error="m").svg_inline(
            scale=4, dark="#0E1330", light=None
        )
    )

    flow = FlowRecord(
        flow_id="flw_" + secrets.token_urlsafe(16),
        consent_id=payload["consent_id"],
        phone_number=body.phone_number,
        context_event=body.event,
        authorization_url=payload["authorization_url"],
        qr_svg=qr_svg,
        created_at=_now(),
        expires_at=datetime.fromisoformat(payload["expires_at"]),
    )
    flows.add(flow)

    return {
        "flow_id": flow.flow_id,
        "expires_at": payload["expires_at"],
        "authorization_url": flow.authorization_url,
        "qr_svg": qr_svg,
    }


async def _poll_and_maybe_complete(flow: FlowRecord) -> None:
    """Best-effort: Isnad being briefly unreachable must surface as "still
    polling", not as a 500 to the operator's browser, and must never leave
    `verifying` stuck True — that would permanently block this flow from ever
    completing."""
    try:
        async with httpx.AsyncClient(base_url=ISNAD_BASE_URL, timeout=15.0) as client:
            status_response = await client.get(
                f"/v1/consents/{flow.consent_id}",
                headers={"Authorization": f"Bearer {ISNAD_MERCHANT_API_KEY}"},
            )
            if status_response.status_code != 200:
                return
            consent_status = status_response.json().get("status")
            flow.status = consent_status

            if consent_status != "AUTHORIZED":
                return
            # Compare-and-swap-by-lock: a flow's own httpx round trip to
            # Isnad's single-use /verify must happen at most once from this
            # harness, even if two browser tabs poll the same flow
            # concurrently.
            with flow.lock:
                if flow.verifying or flow.result is not None:
                    return
                flow.verifying = True
            try:
                verify_response = await client.post(
                    f"/v1/consents/{flow.consent_id}/verify",
                    headers={"Authorization": f"Bearer {ISNAD_MERCHANT_API_KEY}"},
                )
                if verify_response.status_code == 200:
                    flow.result = verify_response.json()
                    flow.status = "COMPLETED"
            finally:
                flow.verifying = False
    except httpx.HTTPError:
        return


@app.get("/api/flows/{flow_id}")
async def get_flow(
    flow_id: str,
    pilot_session: str | None = Cookie(default=None),
) -> dict:
    _require_session(pilot_session)
    flow = flows.get(flow_id)
    if flow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no such flow")

    if flow.result is None and flow.status not in {"DENIED", "FAILED", "EXPIRED"}:
        await _poll_and_maybe_complete(flow)

    return {
        "flow_id": flow.flow_id,
        "status": flow.status,
        "authorization_url": flow.authorization_url,
        "qr_svg": flow.qr_svg,
        "result": flow.result,
    }
