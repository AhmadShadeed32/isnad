"""Bind a reviewer-supplied model key to one request, then let it go.

Raw ASGI rather than `BaseHTTPMiddleware` for the same reason the other two
middlewares here are: this has to wrap every response including the SSE stream,
and a `ContextVar` set in a `BaseHTTPMiddleware` does not reliably reach the
endpoint, which would make the key silently do nothing.

The reset in `finally` is the whole safety property. Workers are reused, so a
key left bound would be spent by whoever asked next.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from app.runtime_keys import (
    GEMINI_KEY_HEADER,
    PLANNER_HEADER,
    accepts_request_key,
    reset_request_gemini_key,
    reset_request_planner,
    set_request_gemini_key,
    set_request_planner,
)


class RequestKeyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not accepts_request_key():
            await self.app(scope, receive, send)
            return

        supplied = None
        planner = None
        for name, value in scope.get("headers", ()):
            if name.lower() == PLANNER_HEADER.encode("latin-1"):
                planner = value.decode("latin-1").strip().lower()
            if name.lower() == GEMINI_KEY_HEADER.encode("latin-1"):
                try:
                    supplied = value.decode("latin-1")
                except UnicodeDecodeError:
                    supplied = None

        if supplied is None and planner is None:
            await self.app(scope, receive, send)
            return

        token = set_request_gemini_key(supplied)
        planner_token = set_request_planner(planner)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_request_planner(planner_token)
            reset_request_gemini_key(token)
