"""The judge lab page (I1/I2/I3/I4/I9) — a reader for recorded runs.

There is deliberately no execution endpoint behind this page. Every case a
judge can select was run offline by `scripts/build_lab_artifacts.py` against a
fixed authored fixture, and what the page does is replay the recording. That
is what makes I1's "replay controls scrub the recorded timeline without
resending requests" and "a replay cannot incur additional model spend" true by
construction instead of by promise, and it is why I9's input surface is
bounded: the only thing a selection can do is pick a recording that already
exists.

The bundle is committed, so it goes stale the moment the policy file or the
code moves. Rather than hide that, the page is handed the *live* policy digest
and code revision alongside the recorded ones and says plainly when they
differ.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.rate_limit import limit_per_ip
from app.ui import page_path

router = APIRouter(tags=["lab"])

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
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


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
