from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response

from app import __version__, retention
from app.api import (
    routes_assets,
    routes_challenge,
    routes_consent,
    routes_console,
    routes_i18n,
    routes_judge,
    routes_lab,
    routes_network_conditions,
    routes_outcomes,
    routes_privacy,
    routes_proof_shares,
    routes_receipt,
    routes_registry,
    routes_reverse,
    routes_session,
    routes_verified_caller,
    routes_verify,
)
from app.api.request_limits import RequestLimitsMiddleware
from app.api.security_headers import SecurityHeadersMiddleware
from app.chain.vault import vault
from app.config import check_startup_posture, makes_billable_calls, settings
from app.session.manager import sessions


def _check_registry_signature() -> None:
    """Verify the number registry before serving anything.

    The Directory verifies lazily on first lookup, which would surface a
    tampered registry as a 500 on whichever request happened to touch it first —
    mid-demo, looking like an unrelated failure. Checking here means a tampered
    file is a server that does not start, which is the honest failure.
    """
    from app.registry.signing import verify

    state = verify(Path(str(settings.registry_path)), required=settings.registry_signature_required)
    if state:
        # Unsigned is allowed unless required, but never silently: a registry
        # nobody signed is a list of banks nobody vouched for.
        logging.getLogger("isnad").warning("number registry is %s", state)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.database import init_db

    check_startup_posture(settings)  # refuse an unsafe billable deployment
    # Route imports must not persist a key before the posture check above.  The
    # stable vault object is configured only now, and the billable path is never
    # allowed to create a replacement for a missing mounted key.
    vault.configure(settings.vault_key_path, allow_create=not makes_billable_calls(settings))
    init_db()  # ensure chain tables exist
    _check_registry_signature()
    # Sweep once at boot as well as on the timer: a process that restarts more
    # often than the interval would otherwise never sweep at all.
    await retention.purge_once_async()
    sweeper = retention.start()
    yield
    if sweeper is not None:
        sweeper.cancel()
    # Cancel any live session monitors on shutdown.
    await sessions.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Isnad — Trust Engine API",
        version=__version__,
        description="Agentic network-verified trust engine (CAMARA / Nokia Network-as-Code).",
        lifespan=lifespan,
        # /docs, /redoc and /openapi.json all answered 200 unauthenticated,
        # publishing the whole route surface to anyone who asked (S12). They
        # follow demo mode: useful locally, absent on a deployed host.
        docs_url="/docs" if settings.demo_mode else None,
        redoc_url="/redoc" if settings.demo_mode else None,
        openapi_url="/openapi.json" if settings.demo_mode else None,
    )
    # Raw ASGI, and added before the routers so it wraps every response
    # including the SSE stream (S10, S12).
    app.add_middleware(RequestLimitsMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(routes_verify.router)
    app.include_router(routes_challenge.router)
    app.include_router(routes_outcomes.router)
    app.include_router(routes_consent.router)
    app.include_router(routes_consent.page_router)
    app.include_router(routes_reverse.router)
    app.include_router(routes_session.router)
    app.include_router(routes_console.router)
    app.include_router(routes_console.page_router)
    app.include_router(routes_judge.page_router)
    app.include_router(routes_lab.router)
    app.include_router(routes_receipt.router)
    app.include_router(routes_privacy.router)
    app.include_router(routes_registry.router)
    app.include_router(routes_verified_caller.router)
    app.include_router(routes_i18n.router)
    # Order matters: routes_assets owns the `/ui/{path}` catch-all, so the
    # i18n router's own `/ui/i18n.js` and `/ui/i18n/{locale}.json` must be
    # mounted ahead of it or they resolve to an unregistered-asset 404.
    app.include_router(routes_assets.router)
    app.include_router(routes_network_conditions.router)
    app.include_router(routes_network_conditions.callback_router)
    app.include_router(routes_proof_shares.router)
    app.include_router(routes_proof_shares.page_router)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        """Land a visitor on the right entry point (P2).

        In demo mode, `/judge` is the focused, plain-language demonstration —
        the entry point this package exists to make honest. Read from
        `settings` at request time, not captured at app-creation time, so a
        test that monkeypatches `settings.demo_mode` sees the change without
        rebuilding the app. Outside demo mode this is unchanged from before:
        the full authenticated console, with its existing credential gating
        untouched.
        """
        return RedirectResponse(url="/judge" if settings.demo_mode else "/console")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        """Liveness only.

        It used to return provider, planner and demo_mode unauthenticated, which
        tells an attacker whether calls cost money and whether the demo write
        endpoints are live — and shows a curious judge "provider":"mock" (S13).
        The console needs those three, so they moved to /v1/console/mode, which
        requires a key.
        """
        return {"status": "ok"}

    @app.get("/readyz", tags=["meta"])
    async def readyz() -> Response:
        """Readiness: the process can reach its already-migrated database.

        `/health` intentionally stays a liveness check. Container orchestration
        must not route paid work to an instance that has started a process but
        cannot use its evidence store, so the image healthcheck uses this probe.
        """
        from app.db.database import database_ready

        if not database_ready():
            return Response(
                content='{"status":"not_ready"}',
                status_code=503,
                media_type="application/json",
            )
        return Response(content='{"status":"ready"}', media_type="application/json")

    return app


app = create_app()
