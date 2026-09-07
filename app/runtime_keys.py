"""A model key a reviewer supplies for one request, and nothing longer.

A judge should be able to watch the Gemini agent choose without editing a
`.env`, and without being handed ours. So the demo accepts a key on the request
itself. That is only safe if the key's lifetime is exactly the request:

* it lives in a `ContextVar`, set by middleware and reset in a `finally`, so it
  cannot survive into the next request on the same worker;
* nothing writes it anywhere — not the database, not a verdict, not a receipt,
  not a log line, not a response body;
* it is honoured only in demo mode, so a billable deployment can never be
  steered by a header a stranger sent.

The signed receipt is the reason the last point matters more than it looks. A
verdict says which planner actually chose. If an attacker could swap the model
behind a deployment by adding a header, that sentence would stop being true.

Nokia credentials are deliberately NOT accepted this way. A model key spends
the judge's own quota on their own say-so; an operator key spends money on
billable network calls, and no public page should be able to trigger those.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

from app.config import settings

# The header a reviewer's browser sends. Read once per request, never stored.
GEMINI_KEY_HEADER = "x-isnad-gemini-key"
PLANNER_HEADER = "x-isnad-planner"
_request_planner: ContextVar[str | None] = ContextVar("isnad_request_planner", default=None)


def set_request_planner(value: str | None) -> Token:
    return _request_planner.set(value if value in {"greedy", "llm"} else None)


def reset_request_planner(token: Token) -> None:
    _request_planner.reset(token)


def requested_planner() -> str:
    return _request_planner.get() or ("llm" if request_gemini_key() else settings.planner)

# A key is rejected before it is ever used if it does not look like one, so a
# stray value cannot become a confusing upstream 400 that mentions the input.
_MAX_KEY_LENGTH = 200

_request_gemini_key: ContextVar[str | None] = ContextVar(
    "isnad_request_gemini_key", default=None
)


def set_request_gemini_key(value: str | None) -> Token:
    """Bind a key to the current request context. Returns the reset token."""
    cleaned = (value or "").strip()
    if not cleaned or len(cleaned) > _MAX_KEY_LENGTH or not cleaned.isprintable():
        cleaned = ""
    return _request_gemini_key.set(cleaned or None)


def reset_request_gemini_key(token: Token) -> None:
    _request_gemini_key.reset(token)


def request_gemini_key() -> str | None:
    """The key this request supplied, if any. Never a configured one."""
    return _request_gemini_key.get()


def effective_gemini_key() -> str | None:
    """The key the model client should use: the request's, else the server's.

    The request's wins so a reviewer's own key is used even on a deployment
    that has one configured — they asked for their run to be theirs.
    """
    if _request_planner.get() == "greedy":
        return None
    return request_gemini_key() or settings.gemini_api_key


def accepts_request_key() -> bool:
    """Whether a request may supply a key at all.

    Demo mode only. `makes_billable_calls` is checked too rather than assumed
    from demo mode, because the two are configured separately and a deployment
    that manages to be both should take the safer reading.
    """
    from app.config import makes_billable_calls

    return bool(settings.demo_mode) and not makes_billable_calls(settings)
