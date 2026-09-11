from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.deps import require_read_access
from app.api.rate_limit import limit_per_key
from app.chain.subject import idempotency_fingerprint
from app.db import challenges, store
from app.domain.enums import Decision
from app.domain.schemas import (
    ChallengeCreateRequest,
    ChallengeCreateResponse,
    ChallengeEventRequest,
    ChallengeEventResponse,
    ChallengeTimelineResponse,
)

router = APIRouter(prefix="/v1", tags=["challenge"], dependencies=[Depends(limit_per_key)])

# These are writes, but they are the *merchant's own* follow-up record on a
# chain the caller already owns: no provider call, no model call, no spend. A
# judge running the paired demonstration has to be able to complete the
# follow-up on their own CHALLENGE result, so a judge session authenticates
# here exactly like a merchant key — and resolves to its own owner, so
# `_owned_challenged_chain` still refuses another tenant's chain with the same
# 404 a missing one gets. The name changed from `_key` to `_owner` because that
# is what the dependency now returns.

_CHAIN_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "chain_not_found", "message": "No such chain"},
)


def _idempotency_key(
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=128),
) -> str:
    return idempotency_key


async def _owned_challenged_chain(chain_id: str):
    """The chain this caller owns, or the same 404 a missing one gets (P3
    mirrors store._owned: existence must not be probeable across owners)."""
    rec = await store.get_record_async(chain_id)
    if rec is None:
        raise _CHAIN_NOT_FOUND
    return rec


@router.post(
    "/chains/{chain_id}/challenges",
    response_model=ChallengeCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_challenge(
    chain_id: str,
    body: ChallengeCreateRequest,
    _owner: str = Depends(require_read_access),
    idempotency_key: str = Depends(_idempotency_key),
) -> ChallengeCreateResponse:
    """Open a followup on a CHALLENGE decision. Refused on any other decision:
    a followup exists to record what happened after CHALLENGE, not to attach
    itself to ALLOW or DECLINE."""
    rec = await _owned_challenged_chain(chain_id)
    if rec.verdict.decision != Decision.CHALLENGE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "not_challenged", "message": "This chain's decision is not CHALLENGE"},
        )
    fingerprint = idempotency_fingerprint("challenge.create", chain_id, body=body)
    try:
        outcome = await asyncio.to_thread(
            challenges.create_attempt,
            chain_id=chain_id,
            method=body.method,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
    except challenges.IdempotencyKeyConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_key_reused",
                "message": "Idempotency-Key was already used for a different request",
            },
        ) from exc
    return ChallengeCreateResponse(**outcome.response)


@router.post(
    "/chains/{chain_id}/challenges/{attempt_id}/events",
    response_model=ChallengeEventResponse,
)
async def report_challenge_event(
    chain_id: str,
    attempt_id: str,
    body: ChallengeEventRequest,
    _owner: str = Depends(require_read_access),
    idempotency_key: str = Depends(_idempotency_key),
) -> ChallengeEventResponse:
    """Report what the merchant found. Only one terminal result is kept per
    attempt: a retry with the same key replays it, a conflicting report
    (a different key against an already-resolved attempt) is a 409."""
    await _owned_challenged_chain(chain_id)
    fingerprint = idempotency_fingerprint("challenge.event", chain_id, attempt_id, body=body)
    try:
        outcome = await asyncio.to_thread(
            challenges.report_event,
            chain_id=chain_id,
            attempt_id=attempt_id,
            result=body.result,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
    except challenges.AttemptNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "attempt_not_found", "message": "No such challenge attempt"},
        ) from exc
    except challenges.AttemptNotPending as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "attempt_not_pending",
                "message": f"Attempt already resolved as {exc.status}",
            },
        ) from exc
    except challenges.IdempotencyKeyConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_key_reused",
                "message": "Idempotency-Key was already used for a different request",
            },
        ) from exc
    return ChallengeEventResponse(**outcome.response)


@router.get("/chains/{chain_id}/challenges", response_model=ChallengeTimelineResponse)
async def get_challenge_timeline(
    chain_id: str,
    _owner: str = Depends(require_read_access),
) -> ChallengeTimelineResponse:
    """The owned followup history for a chain. Available on any decision —
    empty on ALLOW/DECLINE and on a CHALLENGE chain with no attempts yet —
    because a read costs nothing and a merchant checking is not an error."""
    await _owned_challenged_chain(chain_id)
    attempts = await asyncio.to_thread(challenges.timeline, chain_id=chain_id)
    return ChallengeTimelineResponse(chain_id=chain_id, attempts=attempts)
