from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import HTMLResponse, StreamingResponse

from app import announce, velocity
from app.agent.investigator import build_engine_for_pricing, build_investigator
from app.agent.planner import effective_planner
from app.api import demo_token, stream_token
from app.api.deps import key_from_bearer, owner_for, require_api_key
from app.api.rate_limit import limit_per_ip, limit_per_key
from app.chain.subject import request_commitment
from app.config import settings
from app.db import store
from app.domain.schemas import Area, Money, RequestContext, VerificationRequest
from app.events import current_owner, emit, subscribe
from app.policy import counterfactual
from app.providers import mock as mock_provider
from app.providers.mock import MockProvider
from app.screening import screen_call

router = APIRouter(prefix="/v1", tags=["console"], dependencies=[Depends(limit_per_key)])
# /console is reachable without a key, so it is limited by address.
page_router = APIRouter(tags=["console"], dependencies=[Depends(limit_per_ip)])

_CONSOLE_HTML = Path(__file__).parent.parent / "static" / "console.html"

# A synthetic claimed location for demo acts whose story assumes the customer
# made one. This is a demo INPUT to the location check — what the customer
# claims — never an observed subscriber location, and it must never be
# persisted into an EvidenceLink, prompt or receipt.
_DEMO_CLAIMED_LOCATION = Area(lat=31.9539, lon=35.9106, radius_m=2000)

# The forward demo acts, keyed for the console trigger buttons.
# (Act IV — Reverse Isnad — is dispatched separately below.)
DEMO_ACTS: dict[str, VerificationRequest] = {
    "act1": VerificationRequest(
        phone_number="+99999991001",
        context=RequestContext(event="signup", account_age_days=0),
    ),
    # Act II — the ghost: a swap inside the window, a new device, and a claimed
    # location the network places the device somewhere else than.
    "act2": VerificationRequest(
        phone_number="+99999991000",
        context=RequestContext(
            event="checkout",
            payment_method="cod",
            account_age_days=0,
            amount=Money(value=4200),
            claimed_location=_DEMO_CLAIMED_LOCATION,
        ),
    ),
    "act3": VerificationRequest(
        phone_number="+99999991002",
        context=RequestContext(
            event="checkout",
            payment_method="cod",
            account_age_days=0,
            amount=Money(value=1500),
        ),
    ),
    # Act V — the gap: consent withheld, one operator that cannot answer.
    # The chain is incomplete rather than contradicted -> CHALLENGE / UNRESOLVED.
    "act5": VerificationRequest(
        phone_number="+99999991005",
        context=RequestContext(
            event="checkout",
            payment_method="cod",
            account_age_days=0,
            amount=Money(value=900),
        ),
    ),
    # Act VI — the lost phone: a genuine SIM replacement three days ago.
    # A rules engine declines on SIM_SWAPPED alone; the agent keeps going and
    # steps up instead -> CHALLENGE / DEGRADED.
    "act6": VerificationRequest(
        phone_number="+99999991006",
        context=RequestContext(
            event="checkout",
            payment_method="cod",
            account_age_days=0,
            amount=Money(value=1500),
            claimed_location=_DEMO_CLAIMED_LOCATION,
        ),
    ),
}


# Placeholder the page carries in place of a credential. Substituted at render
# time with a freshly minted short-TTL token, or with an empty string when demo
# mode is off — in which case the console asks the presenter for a real key.
_TOKEN_PLACEHOLDER = "__ISNAD_CONSOLE_TOKEN__"


@page_router.get("/console")
async def console_page() -> HTMLResponse:
    """Serve the live agent console (terminal-styled demo UI).

    The page used to ship `Authorization: Bearer demo-merchant-key` in its
    source, so view-source on a public URL yielded a working merchant
    credential (S1). It now carries a placeholder, replaced here by a token that
    expires — and only when demo mode is on.
    """
    token = demo_token.mint() if settings.demo_mode else ""
    html = _CONSOLE_HTML.read_text(encoding="utf-8").replace(_TOKEN_PLACEHOLDER, token)
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "no-store"},  # a minted token must not be cached
    )


# How often to write a comment frame down an idle stream. Without one, an
# intermediate proxy silently drops the judges' console mid-presentation, and a
# subscriber that has gone away is never noticed because nothing is ever written
# to it (S12).
SSE_KEEPALIVE_SECONDS = 15


@router.get("/console/mode")
async def console_mode(_key: str = Depends(require_api_key)) -> dict:
    """What the console needs to label the run honestly.

    Behind a key because /health used to answer this to anyone (S13): whether
    calls cost money, and whether the demo write endpoints are live, are both
    things an attacker wants and a stranger should not get.
    """
    return {
        "provider": settings.provider,
        # The effective planner, not the configured one: an `llm` pill over a
        # run greedy is choosing is the console's most testable false claim.
        "planner": effective_planner(),
        "demo_mode": settings.demo_mode,
    }


@router.post("/console/stream-token")
async def console_stream_token(_key: str = Depends(require_api_key)) -> dict:
    """Exchange a normal bearer key for a short-lived SSE-only credential.

    Browser ``EventSource`` cannot send ``Authorization``.  The console first
    calls this route with its normal header, then places only this opaque,
    non-API token in the stream URL.  It carries the owner required for
    isolation, but cannot call any other route.
    """
    try:
        token = stream_token.mint(owner_for(_key))
    except stream_token.StreamTokenCapacityExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "stream_capacity_exceeded",
                "message": "Too many active streams; retry shortly",
            },
        ) from exc
    return {"stream_token": token, "expires_in_seconds": stream_token.STREAM_TOKEN_TTL_SECONDS}


@router.get("/console/stream")
async def console_stream(
    authorization: str = Header(default=""),
    stream_credential: str | None = Query(default=None, alias="stream_token"),
) -> StreamingResponse:
    """Server-Sent Events stream of the live agent console.

    Each verification emits: start -> evidence (per link) -> verdict, and each
    subscriber receives only the events belonging to its own key (S2). This used
    to be unauthenticated and process-wide, so `curl -N /v1/console/stream`
    harvested every tenant's hypotheses, evidence signals and chain_ids live.

    A normal bearer key is accepted only in ``Authorization``.  Browser
    EventSource connections use a separately minted, stream-only token in the
    query string; request logs therefore never contain a merchant credential.
    """
    key = key_from_bearer(authorization)
    owner = owner_for(key) if key is not None else stream_token.owner_for(stream_credential or "")
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_api_key", "message": "Bearer API key required"},
        )

    async def gen():
        try:
            events = subscribe(owner)
            while True:
                try:
                    event = await asyncio.wait_for(
                        events.__anext__(), timeout=SSE_KEEPALIVE_SECONDS
                    )
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                except StopAsyncIteration:  # pragma: no cover
                    return
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:  # pragma: no cover
            return
        finally:
            await events.aclose()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


# Reverse Isnad demo (Act IV): a spoofed "bank officer" caller.
SPOOFED_CALLER = "+96279999999"

# --- Act VII — the bank that wasn't -----------------------------------------
# One institution, three calls presenting numbers that belong to it, and three
# different answers. The act exists to make one point on stage: a registry hit
# is not trust. Only the announced call verifies.
# NOT the registry's `demo-bank-jo`. The console mints a token to any visitor
# while demo mode is on, and that token satisfies `_act7_key`, so an anonymous
# visitor can create this announcement. An announcement is a record of an
# institution asserting it is about to place a call, and one written by a
# stranger must not carry the registered institution's id into that record.
# Under a DEMO id the row says what it is: the console's own fixture, not
# Demo Bank speaking. `display_name` stays "Demo Bank" because that is what the
# announcement is FOR — the brand shown on the ringing phone — and the stage
# needs it.
ACT7_INSTITUTION = "DEMO-console-act7"
ACT7_SWITCHBOARD = "+96265000000"  # the bank does call from this
ACT7_HOTLINE = "+96280022222"  # published inbound-only; never originates
ACT7_CUSTOMER = "+962790000001"

# Act VIII — the honest limit. An extension inside the bank's published DID
# block: the registry resolves it by prefix, and the network can say nothing
# about it at all, because a PBX trunk has no SIM. The right answer is a chain
# with a hole in it, not a guess in either direction.
BANK_LANDLINE = "+96265000123"


@router.post("/console/run/{act}")
async def console_run(
    act: str,
    run_id: str | None = Header(default=None, alias="X-Console-Run-Id"),
    authorization: str = Header(default=""),
) -> dict:
    """Trigger a demo act server-side (paced), emitting to the live stream.

    Demo-only, and now behind a key (S4). It used to be unauthenticated, so a
    stranger could fire acts into the judges' console mid-presentation and write
    a permanent signed row per call with no rate limit. The console already
    sends its token; requiring it costs the demo nothing.
    """
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "demo_disabled"})
    key = key_from_bearer(authorization)
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_api_key", "message": "Bearer API key required"},
        )
    # Attributing the run to the caller is what puts the act's events on the
    # presenter's own stream rather than on everybody's (S2).
    current_owner.set(owner_for(key))
    paced = MockProvider(step_delay_ms=650)

    if act in ("act4", "act8"):
        # Reverse Isnad — verify an inbound caller to the customer.
        from app.api.routes_reverse import run_reverse

        subject = SPOOFED_CALLER if act == "act4" else BANK_LANDLINE
        verdict = await run_reverse(subject, paced, run_id=run_id, claimed_identity="Demo Bank")
        body = subject
    else:
        req = DEMO_ACTS.get(act)
        if req is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "unknown_act", "message": f"No demo act '{act}'"},
            )
        subject = req.phone_number
        verdict = await build_investigator(paced).investigate(req, run_id=run_id)
        body = req

    # A demo chain binds to its subject like any other, so the receipt page and
    # the vault act behave identically on stage and in production (S5).
    await store.save_async(
        verdict,
        subject=subject,
        request_hash=request_commitment(body),
    )
    # The Act buttons are the live stage path, so they must surface the same
    # T5 comparison as /v1/verify. Reverse acts do not model the merchant OTP
    # alternative, and deliberately leave it absent.
    alternative = (
        counterfactual.compute(verdict, subject, build_engine_for_pricing())
        if act in DEMO_ACTS
        else None
    )
    return {
        "decision": verdict.decision.value,
        "confidence": verdict.confidence,
        "hypothesis": verdict.hypothesis,
        "reason": verdict.reason,
        "chain_grade": verdict.chain_grade.value,
        "chain_id": verdict.chain_id,
        "alternative": alternative,
    }


def _act7_key(authorization: str) -> str:
    """Same gate as console_run: demo mode, plus a valid console token."""
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "demo_disabled"})
    key = key_from_bearer(authorization)
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_api_key", "message": "Bearer API key required"},
        )
    current_owner.set(owner_for(key))
    return key


@router.post("/console/act7/announce")
async def act7_announce(
    run_id: str | None = Header(default=None, alias="X-Console-Run-Id"),
    authorization: str = Header(default=""),
) -> dict:
    """The bank declares the call it is about to place.

    This writes the announcement directly rather than going through
    /v1/verified-caller/pre-announce, because that endpoint requires the key to
    be bound to an institution via ISNAD_INSTITUTION_KEYS and a demo box has no
    such binding. The bypass is safe only because of what it is NOT: demo mode
    is required, the endpoint takes no parameters, and the institution and both
    numbers are constants in this file. Nothing a caller sends chooses who is
    announced — which is the property the real endpoint spends its two checks
    establishing.
    """
    key = _act7_key(authorization)
    announcement_id, expires_at = await announce.record_async(
        institution_id=ACT7_INSTITUTION,
        api_key=key,
        calling_participant=ACT7_SWITCHBOARD,
        called_participant=ACT7_CUSTOMER,
        strategy="BRAND_DISPLAY",
        display_name="Demo Bank",
        call_reason="Re: your loan application",
    )
    ttl = int((expires_at - datetime.now(UTC)).total_seconds())
    await _act7_emit(
        {
            "type": "announce",
            "institution": "Demo Bank",
            "calling_participant": ACT7_SWITCHBOARD,
            "announcement_id": announcement_id,
            "ttl_seconds": max(ttl, 0),
        },
        run_id,
    )
    return {"announcement_id": announcement_id, "ttl_seconds": max(ttl, 0)}


@router.post("/console/act7/screen/{target}")
async def act7_screen(
    target: str,
    run_id: str | None = Header(default=None, alias="X-Console-Run-Id"),
    authorization: str = Header(default=""),
) -> dict:
    """Screen one of the three Act VII calls. Tier 1, no network call."""
    _act7_key(authorization)
    caller = {
        # The announced call and the spoofed one present the SAME number. That
        # is the whole demonstration: the difference is not the number.
        "announced": ACT7_SWITCHBOARD,
        "spoofed": ACT7_SWITCHBOARD,
        "hotline": ACT7_HOTLINE,
    }.get(target)
    if caller is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "unknown_target", "message": f"No Act VII target '{target}'"},
        )
    # "spoofed" screens against a callee nobody announced a call to, so a live
    # announcement for the real customer does not rescue it.
    callee = ACT7_CUSTOMER if target != "spoofed" else "+962790009999"
    result = await screen_call(caller, callee, claimed_identity="Demo Bank")
    await _act7_emit(
        {
            "type": "screen",
            "label": result.label,
            "reason": result.reason,
            "basis": result.basis,
            "caller_number": result.caller_number,
            "institution_name": result.institution_name,
            "elapsed_us": result.elapsed_us,
            "target": target,
        },
        run_id,
    )
    return result.model_dump()


async def _act7_emit(event: dict, run_id: str | None) -> None:
    if run_id:
        event["run_id"] = run_id
    await emit(event)


@router.post("/console/reset-stage")
async def reset_stage(authorization: str = Header(default="")) -> dict:
    """Clear the two local state stores that can change a later stage beat.

    The endpoint has no caller-supplied target, is demo-gated through
    ``_act7_key``, and touches only velocity observations and the mock's
    in-memory SIM-swap simulation. It never resets evidence chains or caller
    configuration.
    """
    _act7_key(authorization)
    cleared_velocity_events = await asyncio.to_thread(velocity.purge_older_than, 0)
    mock_provider.clear_tripped_swaps()
    return {
        "cleared_velocity_events": cleared_velocity_events,
        "cleared_simulated_swaps": True,
    }


@router.post("/console/velocity-demo")
async def velocity_demo(
    run_id: str | None = Header(default=None, alias="X-Console-Run-Id"),
    authorization: str = Header(default=""),
) -> dict:
    """Drive the same Tier 1 path that creates the caller-velocity signal.

    This is intentionally not a database fixture: it demonstrates that ordinary
    screens, from one tenant, build the cross-call signal. The target number and
    callee pattern are constants so the demo route cannot become a way to write
    arbitrary observations for arbitrary callers.
    """
    _act7_key(authorization)
    threshold = build_engine_for_pricing().velocity_threshold()
    calls = max(40, threshold + 1)
    for index in range(calls):
        await screen_call(ACT7_SWITCHBOARD, f"+96279{index:06d}")
    result = await screen_call(ACT7_SWITCHBOARD, ACT7_CUSTOMER)
    await _act7_emit(
        {
            "type": "velocity",
            "calls": calls,
            "threshold": threshold,
            "label": result.label,
            "basis": result.basis,
            "reason": result.reason,
        },
        run_id,
    )
    return {
        "calls": calls,
        "threshold": threshold,
        "label": result.label,
        "basis": result.basis,
        "reason": result.reason,
    }
