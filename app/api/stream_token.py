"""Short-lived, stream-only credentials for browser EventSource connections.

EventSource cannot attach an Authorization header.  Passing a merchant API key
in its query string makes that long-lived credential visible to intermediaries
which log request URLs.  A caller therefore exchanges the normal bearer key
over a header-authenticated route for an opaque credential that can *only*
subscribe to the console event stream.
"""

from __future__ import annotations

import secrets
import time

STREAM_TOKEN_TTL_SECONDS = 300
_MAX_LIVE_TOKENS = 128
_MAX_LIVE_TOKENS_PER_OWNER = 16

# token -> (unix expiry, event-stream owner)
_tokens: dict[str, tuple[float, str]] = {}


class StreamTokenCapacityExceeded(RuntimeError):
    """Minting must not displace another owner's live stream credential."""


def _sweep(now: float) -> None:
    for token, (expires, _) in list(_tokens.items()):
        if expires <= now:
            del _tokens[token]


def mint(owner: str) -> str:
    """Issue a credential that identifies one SSE owner and nothing else."""
    now = time.time()
    _sweep(now)
    if len(_tokens) >= _MAX_LIVE_TOKENS:
        raise StreamTokenCapacityExceeded("stream credential capacity is temporarily full")
    if (
        sum(1 for _, token_owner in _tokens.values() if token_owner == owner)
        >= _MAX_LIVE_TOKENS_PER_OWNER
    ):
        raise StreamTokenCapacityExceeded("stream credential limit reached for this owner")
    token = "stream_" + secrets.token_urlsafe(32)
    _tokens[token] = (now + STREAM_TOKEN_TTL_SECONDS, owner)
    return token


def owner_for(candidate: str) -> str | None:
    """Return the stream owner while the token is valid, otherwise ``None``."""
    now = time.time()
    _sweep(now)
    record = _tokens.get(candidate)
    return record[1] if record is not None and record[0] > now else None


def clear() -> None:
    """Test helper: remove all live stream credentials."""
    _tokens.clear()
