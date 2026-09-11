from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.deps import require_api_key
from app.api.rate_limit import limit_per_key
from app.chain.subject import idempotency_fingerprint
from app.config import settings
from app.db import outcomes, store
from app.domain.schemas import OutcomeEventResponse, OutcomeReportRequest, OutcomeTimelineResponse

router = APIRouter(prefix="/v1", tags=["outcomes"], dependencies=[Depends(limit_per_key)])

_CHAIN_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "chain_not_found", "message": "No such chain"},
)


def _idempotency_key(
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=128),
) -> str:
    return idempotency_key


async def _owned_chain(chain_id: str) -> None:
    """Ownership only — no decision gate. Unlike P3, an outcome may be
    reported on any owned chain, including ALLOW/DECLINE."""
    rec = await store.get_record_async(chain_id)
    if rec is None:
        raise _CHAIN_NOT_FOUND


@router.post(
    "/chains/{chain_id}/outcomes",
    response_model=OutcomeEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def report_outcome(
    chain_id: str,
    body: OutcomeReportRequest,
    _key: str = Depends(require_api_key),
    idempotency_key: str = Depends(_idempotency_key),
) -> OutcomeEventResponse:
    await _owned_chain(chain_id)

    ceiling = datetime.now(UTC) + timedelta(seconds=settings.outcome_future_tolerance_seconds)
    if body.occurred_at > ceiling:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "occurred_at_in_future", "message": "occurred_at is beyond the clock tolerance"},
        )

    fingerprint = idempotency_fingerprint("outcome.report", chain_id, body=body)
    try:
        outcome = await asyncio.to_thread(
            outcomes.report,
            chain_id=chain_id,
            dimension=body.dimension,
            value=body.value,
            basis=getattr(body, "basis", None),
            occurred_at=body.occurred_at,
            late_report=body.late_report,
            supersedes_event_id=body.supersedes_event_id,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
    except outcomes.DimensionAlreadyLabelled as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "dimension_already_labelled",
                "message": "This dimension already has a current report; supply supersedes_event_id to correct it",
            },
        ) from exc
    except outcomes.SupersedeTargetNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "supersede_target_not_found",
                "message": "supersedes_event_id does not name the current report for this chain and dimension",
            },
        ) from exc
    except outcomes.IdempotencyKeyConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_key_reused",
                "message": "Idempotency-Key was already used for a different request",
            },
        ) from exc
    return OutcomeEventResponse(**outcome.response)


@router.get("/chains/{chain_id}/outcomes", response_model=OutcomeTimelineResponse)
async def get_outcomes(
    chain_id: str,
    _key: str = Depends(require_api_key),
) -> OutcomeTimelineResponse:
    await _owned_chain(chain_id)
    data = await asyncio.to_thread(outcomes.current_and_timeline, chain_id=chain_id)
    return OutcomeTimelineResponse(chain_id=chain_id, **data)
