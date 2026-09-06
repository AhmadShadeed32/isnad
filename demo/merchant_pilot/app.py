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

from app.domain.schemas import Area, Money, RequestContext

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
    # R1: the operator session that created this flow. Every read/write must
    # check this before touching the flow at all — authentication alone (any
    # valid operator session) is not the same as authorization (this flow's
    # own creator), and a second valid session must never silently inherit
    # the first's in-flight consent, challenge or outcome state.
    owner_session_id: str
    consent_id: str
    phone_number: str
    context_event: str
    authorization_url: str
    qr_svg: str
    created_at: datetime
    expires_at: datetime
    status: str = "PENDING"
    verifying: bool = False
    # F1: the upstream consent this flow was built on is gone — past its
    # retention window, or revoked. Distinct from "we have not heard yet":
    # nothing further will arrive, so the page must stop implying it might.
    consent_gone: bool = False
    result: dict[str, Any] | None = None
    # The merchant's own followup on a CHALLENGE decision (P3), sourced from
    # Isnad's /v1/chains/{chain_id}/challenges response — never mixed into
    # `result`, which is the signed verdict.
    challenge: dict[str, Any] | None = None
    # Current outcome label per dimension (P5), keyed "order_status" /
    # "fraud_assessment" — available regardless of decision, unlike `challenge`.
    outcomes: dict[str, Any] = field(default_factory=dict)
    # R6: the last attempted outcome-report operation per dimension, frozen
    # (including its `occurred_at`) before it is ever sent. A retry of the
    # same logical action reuses this verbatim instead of generating a fresh
    # timestamp that Isnad's own idempotency fingerprint would then see as a
    # conflicting reuse of the same key.
    pending_outcome_ops: dict[str, dict[str, Any]] = field(default_factory=dict)
    # I8: the trust session bound to this order, plus this harness's own
    # fulfillment decision. `session["status"]` is only ever a snapshot from
    # the last check against Isnad — release-order re-checks it fresh rather
    # than trusting a stale copy.
    session: dict[str, Any] | None = None
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
        """Internal, unauthorized lookup — background completion polling
        only. Every request handler must use `get_owned` instead."""
        with self._lock:
            return self._flows.get(flow_id)

    def get_owned(self, flow_id: str, session_id: str) -> FlowRecord | None:
        """R1 + R3: sweeps expired flows first (retention enforced on every
        read, not only at creation), then returns the flow only if it exists
        and belongs to `session_id` — the same 404 either way from the
        caller's side, so a foreign session cannot distinguish "no such
        flow" from "not yours"."""
        with self._lock:
            self._sweep()
            flow = self._flows.get(flow_id)
            if flow is None or not secrets.compare_digest(flow.owner_session_id, session_id):
                return None
            return flow

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
    # I11: a customer/merchant CLAIM, never an observed phone location. Bounded
    # by the same Area schema Isnad's own RequestContext uses; omitted means
    # "location cannot be verified", never inferred from anything else.
    claimed_location: Area | None = None
    amount: Money | None = None


# I11 step 4: the harness's own Money model (like Isnad's) accepts any
# three-character code. Until a per-currency policy or a reviewed conversion
# contract exists, only the demo's own currency is accepted here — comparing
# an unconverted JOD/SAR amount to a USD-denominated policy threshold would be
# a silent unit error, not a supported feature.
SUPPORTED_CURRENCIES = {"USD"}


_REPORTABLE_RESULTS = {"PASSED", "FAILED", "ABANDONED"}


class ChallengeEventBody(BaseModel):
    result: str


_OUTCOME_DIMENSIONS = {"order_status", "fraud_assessment"}


class OutcomeReportBody(BaseModel):
    dimension: str
    value: str
    basis: str | None = None


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
    if flows.get_owned(flow_id, session.session_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no such flow")
    html = (_STATIC_DIR / "flow.html").read_text(encoding="utf-8")
    html = html.replace("__FLOW_ID__", flow_id).replace("__CSRF_TOKEN__", session.csrf_token)
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
        raw = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="malformed JSON body") from exc
    try:
        body = NewFlowRequest.model_validate(raw)
        # R7: validated by the SAME domain constraints RequestContext itself
        # enforces (its Literal event values, its account_age_days >= 0),
        # constructed inside this same try so a rejection here is also a 422
        # instead of an unhandled ValidationError escaping as a 500 — never a
        # second, looser copy of those rules on NewFlowRequest.
        context = RequestContext(
            event=body.event,
            account_age_days=body.account_age_days,
            claimed_location=body.claimed_location,
            amount=body.amount,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())
    if not _PHONE_PATTERN.match(body.phone_number):
        raise HTTPException(status_code=422, detail="phone_number must be E.164")
    if body.amount is not None and body.amount.currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(
            status_code=422,
            detail=f"unsupported currency {body.amount.currency!r}; only {sorted(SUPPORTED_CURRENCIES)} for now",
        )

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
        owner_session_id=session.session_id,
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
            if status_response.status_code == 404:
                # F1: the upstream consent is gone — expired past retention, or
                # revoked. Preserving whatever this harness last saw would leave
                # an operator watching a state that no longer exists anywhere.
                flow.status = "UNAVAILABLE"
                flow.consent_gone = True
                return
            if status_response.status_code != 200:
                return
            consent_status = status_response.json().get("status")
            flow.status = consent_status

            # R2: a COMPLETED consent with no locally cached result means an
            # earlier /verify call from this harness committed upstream but
            # its response never arrived here (a lost read, a restart). Isnad
            # caches the completed result and returns the SAME one on a
            # repeat call (routes_consent.complete_number_verification) rather
            # than investigating again, so recovering it here can never start
            # a second investigation or buy a second chain/charge.
            should_fetch_result = consent_status == "AUTHORIZED" or (
                consent_status == "COMPLETED" and flow.result is None
            )
            if not should_fetch_result:
                return
            # Compare-and-swap-by-lock: a flow's own httpx round trip to
            # Isnad's /verify must happen at most once at a time from this
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
                # A 409 here means Isnad's own consent is mid-verification
                # from the call that just lost its response; the next poll
                # retries rather than treating this as a hard failure.
            finally:
                flow.verifying = False
    except httpx.HTTPError:
        return


@app.get("/api/flows/{flow_id}")
async def get_flow(
    flow_id: str,
    pilot_session: str | None = Cookie(default=None),
) -> dict:
    session = _require_session(pilot_session)
    flow = flows.get_owned(flow_id, session.session_id)
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
        # F1: COMPLETED is set from the consent *before* the receipt is
        # recovered, so a failed recovery answers COMPLETED with no result. The
        # browser stopped polling on every COMPLETED state and went quiet until
        # a manual reload. Said explicitly here rather than left to be inferred
        # from a null: the flow is upstream-complete but this harness does not
        # hold the receipt yet, and the next poll will try again.
        "recovering": flow.status == "COMPLETED" and flow.result is None,
        # The merchant's own CHALLENGE followup, if any — always a sibling of
        # `result`, never folded into it (P3).
        "challenge": flow.challenge,
        # Current outcome label per dimension (P5) — also a sibling of
        # `result`, available on any decision.
        "outcomes": flow.outcomes,
        # I8: the trust session bound to this order, if one was opened.
        "session": flow.session,
    }


@app.post("/api/flows/{flow_id}/trust-session")
async def open_trust_session(
    flow_id: str,
    request: Request,
    pilot_session: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
) -> dict:
    """I8: open a trust-with-a-TTL session on this order's number, binding it
    to the flow (this harness's stand-in for an order id) so a later release
    can only ever check *this* session, never a caller-supplied one."""
    session = _require_session(pilot_session)
    _require_csrf(request, session, x_csrf_token)
    flow = flows.get_owned(flow_id, session.session_id)
    if flow is None or flow.result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no such flow")

    async with httpx.AsyncClient(base_url=ISNAD_BASE_URL, timeout=15.0) as client:
        response = await client.post(
            "/v1/sessions",
            headers={"Authorization": f"Bearer {ISNAD_MERCHANT_API_KEY}"},
            json={"phone_number": flow.phone_number},
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Isnad rejected the session request")
    data = response.json()
    flow.session = {
        "session_id": data["session_id"],
        "status": data["status"],
        "fulfillment_state": "HELD",
    }
    return flow.session


@app.post("/api/flows/{flow_id}/simulate-swap")
async def simulate_flow_swap(
    flow_id: str,
    request: Request,
    pilot_session: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
) -> dict:
    """Demo control only (I8), mirrors the existing clean-case continuity
    drill: inject a mid-session SIM swap on this flow's own bound session."""
    session = _require_session(pilot_session)
    _require_csrf(request, session, x_csrf_token)
    flow = flows.get_owned(flow_id, session.session_id)
    if flow is None or flow.session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no open trust session for this flow")

    async with httpx.AsyncClient(base_url=ISNAD_BASE_URL, timeout=15.0) as client:
        response = await client.post(
            f"/v1/sessions/{flow.session['session_id']}/simulate-swap",
            headers={"Authorization": f"Bearer {ISNAD_MERCHANT_API_KEY}"},
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Isnad rejected the swap simulation")
    return {"status": response.json().get("status")}


@app.post("/api/flows/{flow_id}/release-order")
async def release_order(
    flow_id: str,
    request: Request,
    pilot_session: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
) -> dict:
    """I8: release fulfillment only if the bound session is CURRENTLY ACTIVE
    — re-checked against Isnad on every call, never assumed from a stale
    local copy. Idempotent once released; refuses (409) if the session has
    moved to REVOKED/EXPIRED/ENDED since it was opened. The lock makes the
    check-then-set atomic against a concurrent release or the swap
    simulation racing it in this same process."""
    session = _require_session(pilot_session)
    _require_csrf(request, session, x_csrf_token)
    flow = flows.get_owned(flow_id, session.session_id)
    if flow is None or flow.session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no open trust session for this flow")

    with flow.lock:
        if flow.session["fulfillment_state"] == "RELEASED":
            return flow.session

        async with httpx.AsyncClient(base_url=ISNAD_BASE_URL, timeout=15.0) as client:
            response = await client.get(
                f"/v1/sessions/{flow.session['session_id']}",
                headers={"Authorization": f"Bearer {ISNAD_MERCHANT_API_KEY}"},
            )
        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Isnad rejected the session lookup")
        current = response.json()
        flow.session["status"] = current["status"]

        if current["status"] != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"session is {current['status']}, not ACTIVE; fulfillment stays held",
            )
        flow.session["fulfillment_state"] = "RELEASED"
        return flow.session


@app.get("/capabilities", response_class=HTMLResponse)
async def capabilities_page(pilot_session: str | None = Cookie(default=None)) -> HTMLResponse:
    """I10's read-only readiness view. Session-gated like every other page in
    this harness; the manifest it renders is fetched from /api/capabilities."""
    if sessions.get(pilot_session) is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return HTMLResponse((_STATIC_DIR / "capabilities.html").read_text(encoding="utf-8"))


@app.get("/api/capabilities")
async def get_capabilities(pilot_session: str | None = Cookie(default=None)) -> dict:
    """I10 read-only readiness view: what is verified, unverified or
    unavailable in the current NaC integration, and why. No provider call —
    this only reads the authored manifest that H2's own recorded captures
    produced."""
    _require_session(pilot_session)
    from app.nac_capabilities import load_capabilities

    return load_capabilities()


@app.post("/api/flows/{flow_id}/outcomes")
async def report_flow_outcome(
    flow_id: str,
    request: Request,
    pilot_session: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
) -> dict:
    """Report or correct an order-status/fraud-assessment label.

    The Idempotency-Key includes the current head's event id (or "none" for a
    first report): a repeat of the exact same click replays, while a second,
    different correction against the same starting point is always a fresh
    write — never a confusing "key reused" conflict for what is, from the
    operator's chair, just clicking a different button.
    """
    session = _require_session(pilot_session)
    _require_csrf(request, session, x_csrf_token)
    flow = flows.get_owned(flow_id, session.session_id)
    if flow is None or flow.result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no such flow")

    try:
        body = OutcomeReportBody.model_validate(await request.json())
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())
    if body.dimension not in _OUTCOME_DIMENSIONS:
        raise HTTPException(status_code=422, detail="dimension must be order_status or fraud_assessment")

    chain_id = flow.result["chain_id"]
    current = flow.outcomes.get(body.dimension)
    supersedes = current["event_id"] if current is not None else "none"
    wants = (body.value, body.basis, supersedes)

    with flow.lock:
        pending = flow.pending_outcome_ops.get(body.dimension)
        if pending is not None and pending["wants"] == wants:
            # The exact same logical action as the last attempt (a button
            # retry after a lost response, a double-click): replay the
            # frozen key and body verbatim, including its original
            # occurred_at, rather than minting a fresh timestamp.
            idempotency_key = pending["key"]
            payload = pending["body"]
        else:
            payload = {
                "dimension": body.dimension,
                "value": body.value,
                "occurred_at": _now().isoformat(),
            }
            if body.basis is not None:
                payload["basis"] = body.basis
            if current is not None:
                payload["supersedes_event_id"] = current["event_id"]
            idempotency_key = f"pilot-outcome-{flow_id}-{body.dimension}-{supersedes}-{body.value}"
            flow.pending_outcome_ops[body.dimension] = {
                "key": idempotency_key,
                "body": payload,
                "wants": wants,
            }

    try:
        async with httpx.AsyncClient(base_url=ISNAD_BASE_URL, timeout=15.0) as client:
            response = await client.post(
                f"/v1/chains/{chain_id}/outcomes",
                headers={
                    "Authorization": f"Bearer {ISNAD_MERCHANT_API_KEY}",
                    "Idempotency-Key": idempotency_key,
                },
                json=payload,
            )
    except httpx.HTTPError as exc:
        # A transport failure here must not surface as an unhandled 500: the
        # write may already have committed upstream (R2's own lesson), and
        # the frozen operation above is exactly what lets a retry recover it
        # safely instead of racing a fresh body against it.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Isnad was unreachable; retry the same action to recover",
        ) from exc

    if response.status_code == status.HTTP_409_CONFLICT:
        raise HTTPException(status_code=409, detail=response.json().get("detail"))
    if response.status_code != status.HTTP_201_CREATED:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Isnad rejected the outcome report")
    flow.outcomes[body.dimension] = response.json()
    with flow.lock:
        flow.pending_outcome_ops.pop(body.dimension, None)
    return flow.outcomes[body.dimension]


@app.post("/api/flows/{flow_id}/challenge")
async def create_flow_challenge(
    flow_id: str,
    request: Request,
    pilot_session: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
) -> dict:
    """Open a followup on this flow's CHALLENGE decision.

    Idempotency-Key is derived from the flow id, not generated fresh: a
    double-submit of this button (a slow network, an impatient click) must
    reopen the same attempt, not mint a second one.
    """
    session = _require_session(pilot_session)
    _require_csrf(request, session, x_csrf_token)
    flow = flows.get_owned(flow_id, session.session_id)
    if flow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no such flow")
    if flow.result is None or flow.result.get("decision") != "CHALLENGE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="this flow's decision is not CHALLENGE"
        )

    chain_id = flow.result["chain_id"]
    async with httpx.AsyncClient(base_url=ISNAD_BASE_URL, timeout=15.0) as client:
        response = await client.post(
            f"/v1/chains/{chain_id}/challenges",
            headers={
                "Authorization": f"Bearer {ISNAD_MERCHANT_API_KEY}",
                "Idempotency-Key": f"pilot-challenge-create-{flow_id}",
            },
            json={"method": "manual_review"},
        )
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Isnad rejected the challenge attempt")
    flow.challenge = response.json()
    return flow.challenge


@app.post("/api/flows/{flow_id}/challenge/events")
async def report_flow_challenge_event(
    flow_id: str,
    request: Request,
    pilot_session: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
) -> dict:
    """Report what the merchant found. One result per attempt: a repeat click
    with the same result replays; a different result after resolution is a 409
    forwarded from Isnad, not silently accepted."""
    session = _require_session(pilot_session)
    _require_csrf(request, session, x_csrf_token)
    flow = flows.get_owned(flow_id, session.session_id)
    if flow is None or flow.challenge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no open challenge attempt for this flow")

    try:
        body = ChallengeEventBody.model_validate(await request.json())
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())
    if body.result not in _REPORTABLE_RESULTS:
        raise HTTPException(status_code=422, detail="result must be PASSED, FAILED or ABANDONED")

    chain_id = flow.result["chain_id"]
    attempt_id = flow.challenge["attempt_id"]
    async with httpx.AsyncClient(base_url=ISNAD_BASE_URL, timeout=15.0) as client:
        response = await client.post(
            f"/v1/chains/{chain_id}/challenges/{attempt_id}/events",
            headers={
                "Authorization": f"Bearer {ISNAD_MERCHANT_API_KEY}",
                "Idempotency-Key": f"pilot-challenge-event-{flow_id}-{attempt_id}-{body.result}",
            },
            json={"result": body.result},
        )
    if response.status_code == status.HTTP_409_CONFLICT:
        raise HTTPException(status_code=409, detail=response.json().get("detail"))
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Isnad rejected the challenge report")
    flow.challenge = {**flow.challenge, **response.json()}
    return flow.challenge
