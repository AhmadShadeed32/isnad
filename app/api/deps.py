from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from app.api import demo_token
from app.config import settings
from app.events import current_owner
from app.judge.access import SESSION_HEADER, JudgeAccessError, JudgeSession
from app.judge.access import access as judge_access
from app.ownership import owner_hash
from app.providers import get_provider


def _valid_key(candidate: str) -> bool:
    # Constant-time comparison against each accepted key (no timing side-channel).
    if any(hmac.compare_digest(candidate, k) for k in settings.api_keys):
        return True
    # A console token is a short-TTL credential minted at render time, and only
    # while demo mode is on. It is deliberately not a configured merchant key.
    if demo_token.is_valid(candidate):
        return True
    # A judge-minted key: issued behind the organizer's access code, owned by
    # the judge session that minted it, and only ever issued on a deployment
    # whose default provider is the mock (app/judge/access.py).
    return judge_access.api_key_owner(candidate) is not None


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
    """The tenant a validated key belongs to.

    A judge-minted key resolves to the judge's own owner BEFORE the hash
    fallback, so the chains it creates are the judge's and not an anonymous
    tenant's that nothing can ever read back.
    """
    return demo_token.owner_for(key) or judge_access.api_key_owner(key) or owner_hash(key)


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


async def require_judge_session(
    judge_session: str = Header(default="", alias=SESSION_HEADER),
) -> JudgeSession:
    """Authenticate a judge by their own scoped session.

    Deliberately separate from `require_api_key`. A judge session is not a
    merchant key and must not become one: it authorizes the paired
    demonstration and nothing else, so it cannot appear on `/v1/verify` or any
    other route that spends on the configured provider. Its owner is its own,
    so two judges never share evidence, quota, receipts or journals.
    """
    try:
        record = judge_access.require(judge_session.strip() or None)
    except JudgeAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    current_owner.set(record.owner)
    return record


async def require_read_access(
    authorization: str = Header(default=""),
    judge_session: str = Header(default="", alias=SESSION_HEADER),
) -> str:
    """Read-only auth for routes a judge and a merchant both legitimately use.

    A judge has to be able to read back their own chain, verify its signature,
    and recover their own run journal — all of which are free of new provider
    and model operations. Accepting a judge session here rather than merging
    every judge into the shared console owner is what keeps one judge's receipt
    and trace out of another's reach.

    Returns the OWNER, not the credential: a judge session and a merchant key
    resolve to owners by different rules, and every caller of this wants the
    answer to "whose rows may this read", never the bearer value itself.
    """
    token = judge_session.strip()
    if token:
        record = judge_access.get(token)
        if record is not None:
            current_owner.set(record.owner)
            return record.owner
    return owner_for(await require_api_key(authorization))
