from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from app.api import demo_token
from app.config import settings
from app.events import current_owner
from app.ownership import owner_hash
from app.providers import get_provider


def _valid_key(candidate: str) -> bool:
    # Constant-time comparison against each accepted key (no timing side-channel).
    if any(hmac.compare_digest(candidate, k) for k in settings.api_keys):
        return True
    # A console token is a short-TTL credential minted at render time, and only
    # while demo mode is on. It is deliberately not a configured merchant key.
    return demo_token.is_valid(candidate)


async def require_api_key(authorization: str = Header(default="")) -> str:
    """Merchant API-key auth: `Authorization: Bearer <key>`."""
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_api_key", "message": "Bearer API key required"},
        )
    key = authorization[len(prefix) :].strip()
    if not _valid_key(key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "invalid_api_key", "message": "Unrecognized API key"},
        )
    # One place decides who the caller is, so everything downstream — the event
    # fan-out (S2), the chain and session stores (S3) — agrees on the answer.
    current_owner.set(owner_for(key))
    return key


def owner_for(key: str) -> str:
    """The tenant a validated key belongs to."""
    return demo_token.owner_for(key) or owner_hash(key)


def key_from_bearer(authorization: str) -> str | None:
    """Extract a validated key from an Authorization header, or None."""
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    key = authorization[len(prefix) :].strip()
    return key if _valid_key(key) else None


def get_live_provider(number_verification_token: str | None = None):
    """Resolve the configured provider as an API-level 503 when unavailable."""
    try:
        return get_provider(number_verification_token=number_verification_token)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "provider_unavailable", "message": str(exc)},
        ) from exc
