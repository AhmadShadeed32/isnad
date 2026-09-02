"""Small ASGI guards that run before FastAPI parses a request body.

Pydantic limits individual fields only after the server has accepted the whole
body. The API has no upload routes, so accepting arbitrarily large bodies is
pure denial-of-service surface. This raw-ASGI middleware deliberately avoids
``BaseHTTPMiddleware`` because buffering would break the SSE console stream.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_REQUEST_BODY_BYTES = 1_048_576
MAX_IN_FLIGHT_REQUESTS = 128


class _RequestBodyTooLarge(Exception):
    pass


async def _reject(send: Send, status: int, code: str, message: str) -> None:
    body = f'{{"detail":{{"code":"{code}","message":"{message}"}}}}'.encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class RequestLimitsMiddleware:
    """Reject oversized bodies and shed excess concurrent HTTP work.

    The in-flight counter has no await between its check and increment, which
    makes it atomic on the event loop without introducing a lock into every
    request. Uvicorn carries the same 128-request ceiling so the process is
    protected before work reaches the ASGI application as well.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_body_bytes: int = MAX_REQUEST_BODY_BYTES,
        max_in_flight: int = MAX_IN_FLIGHT_REQUESTS,
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.max_in_flight = max_in_flight
        self._in_flight = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = next(
            (
                value
                for name, value in scope.get("headers", [])
                if name.lower() == b"content-length"
            ),
            None,
        )
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                await _reject(send, 400, "invalid_content_length", "Invalid Content-Length header")
                return
            if declared < 0 or declared > self.max_body_bytes:
                await _reject(
                    send,
                    413,
                    "request_too_large",
                    f"Request body exceeds {self.max_body_bytes} bytes",
                )
                return

        if self._in_flight >= self.max_in_flight:
            await _reject(
                send,
                503,
                "server_busy",
                "Too many concurrent requests; retry shortly",
            )
            return

        self._in_flight += 1
        response_started = False
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise _RequestBodyTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            # Request parsing happens before an endpoint can start a response.
            # Leave a partially-started response untouched if an unusual ASGI
            # app consumes the body after responding.
            if not response_started:
                await _reject(
                    send,
                    413,
                    "request_too_large",
                    f"Request body exceeds {self.max_body_bytes} bytes",
                )
        finally:
            self._in_flight -= 1
