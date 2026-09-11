"""Recorded Lab exploration plus an explicit, authenticated Gemini simulation.

Reading and replaying the bundle is free of model and operator calls. Only
POST /v1/lab/run/{case_id} executes a model, against a fixed mock case.
The generated run is returned to the requester and never replaces the bundle.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse

from app.api import demo_token
from app.api.deps import require_api_key
from app.api.rate_limit import limit_per_ip
from app.config import settings
from app.runtime_keys import (
    accepts_request_key,
    effective_gemini_key,
    requested_planner,
    uses_server_key,
)
from app.ui import page_path

router = APIRouter(tags=["lab"])
_model_slots = asyncio.Semaphore(2)

_LAB_HTML = page_path("lab")
_BUNDLE = Path(__file__).resolve().parents[2] / "demo" / "lab" / "artifacts" / "bundle.json"

_MISSING_BUNDLE = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={
        "code": "lab_bundle_missing",
        "message": "No lab artifacts have been generated (scripts/build_lab_artifacts.py)",
    },
)


def _read_bundle() -> str:
    """The artifact text as stored. Never parsed and re-serialized: the page
    shows digests over this content, and a round trip through a serializer
    would quietly change the bytes those digests are meant to describe."""
    return _BUNDLE.read_text(encoding="utf-8")


def _live_identity() -> dict:
    from demo.lab.runner import _code_revision, _policy_digest

    revision, dirty = _code_revision()
    return {"code_revision": revision, "dirty": dirty, "policy_digest": _policy_digest()}


def _embed(payload: str) -> str:
    """Close a `</script>` sequence that appears inside the JSON rather than
    letting the HTML parser end the block early. The escape is invisible to
    JSON.parse, so the page still reads the exact same values."""
    return payload.replace("</", "<\\/")


@router.get("/lab", response_class=HTMLResponse, include_in_schema=False)
async def lab_page(request: Request) -> HTMLResponse:
    await limit_per_ip(request)
    html = _LAB_HTML.read_text(encoding="utf-8")
    try:
        bundle = await asyncio.to_thread(_read_bundle)
    except OSError:
        # An honest empty state beats a page that looks broken. The bundle is
        # committed, so this is a packaging problem, not a judge's problem.
        bundle = "null"
    identity = json.dumps(await asyncio.to_thread(_live_identity), sort_keys=True)
    html = html.replace('"__BUNDLE__"', _embed(bundle), 1)
    html = html.replace('"__LIVE_IDENTITY__"', _embed(identity), 1)
    html = html.replace('__ISNAD_LAB_TOKEN__', demo_token.mint() if settings.demo_mode else '')
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


@router.post("/v1/lab/run/{case_id}")
async def lab_model_run(case_id: str, request: Request, _key: str = Depends(require_api_key)):
    """Explicit, model-backed simulation; fixed fixtures and mock network only."""
    from app.agent.planner import LLMPlanner
    from app.policy.engine import get_engine
    from demo.lab.challenge import CASES, run_case

    await limit_per_ip(request)
    if not accepts_request_key():
        raise HTTPException(403, detail="Lab model runs are available only in a non-billable demo")
    if case_id not in CASES:
        raise HTTPException(404, detail="Unknown Lab case")
    if not effective_gemini_key():
        from app.model_budget import budget_exhausted

        if requested_planner() == "llm" and uses_server_key() and budget_exhausted():
            raise HTTPException(
                429,
                detail=(
                    "The site's Gemini allowance is used up for now. Replay the recorded "
                    "Greedy run, try later, or use your own Gemini key."
                ),
            )
        raise HTTPException(400, detail="Select Gemini and configure a server or personal key first")
    if _model_slots.locked():
        raise HTTPException(429, detail="Lab model runs are busy; try again shortly")
    async with _model_slots:
        planner = LLMPlanner(get_engine(str(settings.policy_path)))
        run = await run_case(case_id, planner=planner)
    return {"run": run.to_dict(), "provider": "mock", "requested_planner": "llm"}


@router.get("/lab/bundle.json", include_in_schema=False)
async def lab_bundle(request: Request) -> JSONResponse:
    """The artifacts themselves, so a reader can check the page's arithmetic
    against the rows it was built from rather than take the rendering on
    trust (I3 step 4's download)."""
    await limit_per_ip(request)
    try:
        bundle = await asyncio.to_thread(_read_bundle)
    except OSError as exc:
        raise _MISSING_BUNDLE from exc
    return JSONResponse(
        content=json.loads(bundle),
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="isnad-lab-bundle.json"',
        },
    )
