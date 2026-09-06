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

from app.api.rate_limit import limit_per_ip

router = APIRouter(tags=["i18n"], dependencies=[Depends(limit_per_ip)])

_I18N_DIR = Path(__file__).parent.parent / "static" / "i18n"
_FILES: dict[str, Path] = {"en": _I18N_DIR / "en.json", "ar": _I18N_DIR / "ar.json"}


@router.get("/ui/i18n/{locale}.json")
async def i18n_dictionary(locale: Literal["en", "ar"]) -> dict:
    """`Literal["en", "ar"]` rejects anything else at the routing layer
    itself — FastAPI 404s before this body runs, so a caller can never
    steer `locale` into a path."""
    return json.loads(_FILES[locale].read_text(encoding="utf-8"))
