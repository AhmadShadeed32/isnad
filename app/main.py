from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response

from app import __version__
from app.api import routes_consent, routes_console, routes_reverse, routes_session, routes_verify
from app.config import settings
from app.session.manager import sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.database import init_db

    init_db()  # ensure chain tables exist
    yield
    # Cancel any live session monitors on shutdown.
    await sessions.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Isnad — Trust Engine API",
        version=__version__,
        description="Agentic network-verified trust engine (CAMARA / Nokia Network-as-Code).",
        lifespan=lifespan,
    )
    app.include_router(routes_verify.router)
    app.include_router(routes_consent.router)
    app.include_router(routes_reverse.router)
    app.include_router(routes_session.router)
    app.include_router(routes_console.router)
    app.include_router(routes_console.page_router)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        # Land visitors on the live console.
        return RedirectResponse(url="/console")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {
            "status": "ok",
            "provider": settings.provider,
            "planner": settings.planner,
            "demo_mode": settings.demo_mode,
        }

    return app


app = create_app()
