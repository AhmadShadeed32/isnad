"""Read-only entry point for the concise, judge-facing product demonstration.

The page deliberately has no companion mutation API.  Its checkout animation
drives the existing, authenticated console fixtures and listens to the existing
per-owner SSE stream.  That keeps the polished presentation from becoming a
second (and less reviewed) way to trigger provider calls.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.api import demo_token
from app.api.rate_limit import limit_per_ip
from app.config import settings
from app.ui import page_path

# A render mints a short-lived demo credential, so Judge Mode has the same
# address-level page limit as the full console.  It is not a free token-minting
# endpoint for a refresh loop.
page_router = APIRouter(tags=["judge"], dependencies=[Depends(limit_per_ip)])

_JUDGE_HTML = page_path("judge")
_TOKEN_PLACEHOLDER = "__ISNAD_JUDGE_TOKEN__"


@page_router.get("/judge", response_class=HTMLResponse, include_in_schema=False)
async def judge_page() -> HTMLResponse:
    """Serve the on-stage checkout journey with a short-lived demo token.

    This uses the same minting policy as ``/console``: no credential is put in
    a production render, and a demo render receives a fresh token that expires
    server-side.  It is also explicitly non-cacheable because the page body can
    contain that token.
    """
    token = demo_token.mint() if settings.demo_mode else ""
    html = _JUDGE_HTML.read_text(encoding="utf-8").replace(_TOKEN_PLACEHOLDER, token)
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})
