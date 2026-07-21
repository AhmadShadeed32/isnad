from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Header, HTTPException, status

from app.config import settings
from app.providers import get_provider


def _valid_key(candidate: str) -> bool:
    # Constant-time comparison against each accepted key (no timing side-channel).
    return any(hmac.compare_digest(candidate, k) for k in settings.api_keys)


async def require_api_key(authorization: str = Header(default="")) -> str:
    """Merchant API-key auth: `Authorization: Bearer <key>`."""
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_api_key", "message": "Bearer API key required"},
        )
    key = authorization[len(prefix):].strip()
    if not _valid_key(key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "invalid_api_key", "message": "Unrecognized API key"},
        )
    return key


def get_live_provider(number_verification_token: Optional[str] = None):
    """Resolve the configured provider as an API-level 503 when unavailable."""
    try:
        return get_provider(number_verification_token=number_verification_token)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "provider_unavailable", "message": str(exc)},
        ) from exc
