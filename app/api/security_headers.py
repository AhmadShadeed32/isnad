from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# No security headers existed anywhere in the tree (S10, S12).
#
# The CSP is strict because it can be: console.html has zero external origins —
# no CDN, no font host, no analytics — and that is a property the runbook says to
# keep, partly because a demo venue may be locked down or offline. The one
# concession is 'unsafe-inline', since the page is deliberately a single file
# with its script and styles inline. Given addRow no longer parses any string as
# markup, the CSP is defence in depth rather than the only control.
CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "font-src 'self'; "
    # No external origin may be contacted, and nothing may frame this.
    "frame-ancestors 'none'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "object-src 'none'"
)

HEADERS = {
    b"content-security-policy": CSP.encode("latin-1"),
    b"x-content-type-options": b"nosniff",
    b"referrer-policy": b"no-referrer",
    b"x-frame-options": b"DENY",
    # The console and every API response are per-request and often carry a
    # minted token or a verdict; none of it should sit in a shared cache.
    b"cross-origin-opener-policy": b"same-origin",
}


class SecurityHeadersMiddleware:
    """Attach security headers to every response.

    Written against the raw ASGI interface rather than BaseHTTPMiddleware
    because the SSE stream must keep streaming: BaseHTTPMiddleware buffers a
    StreamingResponse, which would hold the console's events until the
    connection closed.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                present = {name.lower() for name, _ in headers}
                for name, value in HEADERS.items():
                    if name not in present:
                        headers.append((name, value))
            await send(message)

        await self.app(scope, receive, send_with_headers)
