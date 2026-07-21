from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from app.agent.investigator import build_investigator
from app.db import store
from app.domain.schemas import Money, RequestContext, VerificationRequest
from app.events import subscribe
from app.providers.mock import MockProvider
from app.config import settings

router = APIRouter(prefix="/v1", tags=["console"])
page_router = APIRouter(tags=["console"])

_CONSOLE_HTML = Path(__file__).parent.parent / "static" / "console.html"

# The three demo acts, keyed for the console trigger buttons.
DEMO_ACTS: dict[str, VerificationRequest] = {
    "act1": VerificationRequest(
        phone_number="+99999991001",
        context=RequestContext(event="signup", account_age_days=0),
    ),
    "act2": VerificationRequest(
        phone_number="+99999991000",
        context=RequestContext(
            event="checkout", payment_method="cod", account_age_days=0,
            amount=Money(value=4200),
        ),
    ),
    "act3": VerificationRequest(
        phone_number="+99999991002",
        context=RequestContext(
            event="checkout", payment_method="cod", account_age_days=0,
            amount=Money(value=1500),
        ),
    ),
}


@page_router.get("/console")
async def console_page() -> FileResponse:
    """Serve the live agent console (terminal-styled demo UI)."""
    return FileResponse(_CONSOLE_HTML, media_type="text/html")


@router.get("/console/stream")
async def console_stream() -> StreamingResponse:
    """Server-Sent Events stream of the live agent console.

    Each verification emits: start -> evidence (per link) -> verdict.
    """

    async def gen():
        try:
            async for event in subscribe():
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:  # pragma: no cover
            return

    return StreamingResponse(gen(), media_type="text/event-stream")


# Reverse Isnad demo (Act IV): a spoofed "bank officer" caller.
SPOOFED_CALLER = "+96279999999"


@router.post("/console/run/{act}")
async def console_run(
    act: str,
    run_id: str | None = Header(default=None, alias="X-Console-Run-Id"),
) -> dict:
    """Trigger a demo act server-side (paced), emitting to the live stream.

    Unauthenticated on purpose: this is the on-stage demo control, not a
    production endpoint. The verdict is also returned for convenience.
    """
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "demo_disabled"})
    paced = MockProvider(step_delay_ms=650)

    if act == "act4":
        # Reverse Isnad — verify an inbound caller to the customer.
        from app.api.routes_reverse import run_reverse

        verdict = await run_reverse(SPOOFED_CALLER, paced, run_id=run_id)
    else:
        req = DEMO_ACTS.get(act)
        if req is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "unknown_act", "message": f"No demo act '{act}'"},
            )
        verdict = await build_investigator(paced).investigate(req, run_id=run_id)

    store.save(verdict)
    return {
        "decision": verdict.decision.value,
        "confidence": verdict.confidence,
        "hypothesis": verdict.hypothesis,
        "reason": verdict.reason,
        "chain_id": verdict.chain_id,
    }
