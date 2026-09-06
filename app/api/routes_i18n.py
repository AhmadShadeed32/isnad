"""I6 — UI locale dictionaries, served through one explicit allowlisted route.

Locale is UI-only: it never enters a verification request commitment or a
policy decision. Only `en`/`ar` exist; nothing here interpolates a caller-
supplied path into a filesystem lookup.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.rate_limit import limit_per_ip

router = APIRouter(tags=["i18n"], dependencies=[Depends(limit_per_ip)])

_STATIC = Path(__file__).parent.parent / "static"
_I18N_DIR = _STATIC / "i18n"
_FILES: dict[str, Path] = {"en": _I18N_DIR / "en.json", "ar": _I18N_DIR / "ar.json"}
_SWITCH_JS = _STATIC / "i18n.js"


@router.get("/ui/i18n/{locale}.json")
async def i18n_dictionary(locale: Literal["en", "ar"]) -> dict:
    """`Literal["en", "ar"]` rejects anything else at the routing layer
    itself — FastAPI 404s before this body runs, so a caller can never
    steer `locale` into a path."""
    return json.loads(_FILES[locale].read_text(encoding="utf-8"))


@router.get("/ui/i18n.js", include_in_schema=False)
async def i18n_switch() -> Response:
    """The locale switch itself, shared by every page that has one.

    One more explicit, allowlisted route rather than a generic static mount —
    same reason as the dictionaries above. Same origin, so the pages keep
    their zero-external-origin property; one implementation, so the fallback
    rule cannot drift into showing a blank on one page and English on
    another.
    """
    return Response(
        content=_SWITCH_JS.read_text(encoding="utf-8"),
        media_type="application/javascript; charset=utf-8",
    )
