from __future__ import annotations

import secrets
import time

from app.config import settings

# Short-TTL bearer tokens minted for the on-stage console.
#
# The console needs to call authenticated routes, and the old answer was to ship
# a permanent merchant key in the page source — which meant view-source on the
# public URL handed a stranger a working credential (S1). A minted token is a
# strictly better trade: it is not a configured merchant key, it expires, and it
# is only ever issued while `demo_mode` is on. With the shipped production
# posture (`demo_mode=False`, S4) no token is ever minted and the page carries no
# credential at all — the presenter supplies a real key at run time instead.

DEMO_TOKEN_TTL_SECONDS = 900
_MAX_LIVE_TOKENS = 32

# Every console token maps to this one owner rather than to itself. A token is
# minted per page render, so owning by token would mean a reload orphaned every
# chain created before it — the "verify this chain" button would 404 on stage.
# All console viewers are the same tenant, which is exactly right for a demo,
# and demo mode is off in any deployment that matters (S4).
CONSOLE_OWNER = "console"


def owner_for(candidate: str) -> str | None:
    """The owner a console token belongs to, or None if it is not one."""
    return CONSOLE_OWNER if is_valid(candidate) else None


# token -> unix expiry
_tokens: dict[str, float] = {}


def _sweep(now: float) -> None:
    for token, expires in list(_tokens.items()):
        if expires <= now:
            del _tokens[token]


def mint() -> str:
    """Issue a console token. Only callable while demo mode is on."""
    if not settings.demo_mode:
        raise RuntimeError("demo tokens are only minted in demo mode")
    now = time.time()
    _sweep(now)
    # Bound the store: a page refresh loop must not grow memory without limit.
    while len(_tokens) >= _MAX_LIVE_TOKENS:
        del _tokens[min(_tokens, key=_tokens.get)]  # type: ignore[arg-type]
    token = "demo_" + secrets.token_urlsafe(32)
    _tokens[token] = now + DEMO_TOKEN_TTL_SECONDS
    return token


def is_valid(candidate: str) -> bool:
    """True while `candidate` is an unexpired console token."""
    if not settings.demo_mode:
        return False
    now = time.time()
    _sweep(now)
    # Compared by lookup rather than by iteration: the value is a 256-bit random
    # string, so there is no low-entropy prefix for a timing probe to walk.
    expires = _tokens.get(candidate)
    return expires is not None and expires > now


def clear() -> None:
    _tokens.clear()
