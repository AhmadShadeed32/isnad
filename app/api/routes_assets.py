"""Same-origin website assets, with explicit paths and refresh-safe caching."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.runtime_keys import accepts_request_key
from app.ui import ASSETS

router = APIRouter(include_in_schema=False)


@router.get("/ui/settings.json")
async def website_settings() -> dict:
    """Public UI capability only; never expose keys or server configuration."""
    return {
        "accepts_request_key": accepts_request_key(),
        "server_gemini_available": accepts_request_key() and bool(settings.gemini_api_key),
    }


@router.get("/ui/{asset_path:path}")
async def website_asset(asset_path: str) -> FileResponse:
    path = ASSETS.get(asset_path)
    if path is None:
        raise HTTPException(status_code=404, detail="No such UI asset")
    return FileResponse(
        path,
        media_type="text/css" if path.suffix == ".css" else "application/javascript",
        headers={"Cache-Control": "no-cache"},
    )
