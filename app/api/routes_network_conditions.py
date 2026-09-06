"""Owner-scoped network condition routes, and the operator's callback.

Two routers on purpose. The first is a merchant API: every operation is scoped
to the authenticated owner, so one tenant can neither see nor delete another's
subscription. The second is a public endpoint the operator posts to, and its
only credential is the per-subscription bearer token we generated — which is
why it lives apart from the merchant key entirely.

Nothing here touches a verdict. Congestion is shown beside a decision, never
inside one: it cannot raise a fraud score and it cannot waive a check.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app import network_conditions as nc
from app.api.deps import get_live_provider, owner_for, require_api_key
from app.api.rate_limit import limit_per_ip, limit_per_key
from app.domain.schemas import (
    NetworkConditionEvent,
    NetworkConditionQueryRequest,
    NetworkConditionQueryResponse,
    NetworkConditionSubscribeRequest,
    NetworkConditionSubscription,
)

router = APIRouter(
    prefix="/v1/network-conditions",
    tags=["network-conditions"],
    dependencies=[Depends(limit_per_key)],
)
# No merchant key: the operator has no way to hold one. The token in the header
# is bound to a single subscription and is the entire credential.
callback_router = APIRouter(
    prefix="/v1/network-conditions",
    tags=["network-conditions"],
    dependencies=[Depends(limit_per_ip)],
)


def _fail(exc: nc.NetworkConditionError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}
    )


@router.post(
    "/subscriptions",
    response_model=NetworkConditionSubscription,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    body: NetworkConditionSubscribeRequest,
    key: str = Depends(require_api_key),
) -> NetworkConditionSubscription:
    provider = get_live_provider()
    try:
        # The provider SDK is synchronous; the same reasoning as the evidence
        # adapter applies, so it does not block the event loop.
        created = await asyncio.to_thread(
            nc.create, owner_for(key), body.phone_number, provider
        )
    except nc.NetworkConditionError as exc:
        raise _fail(exc) from None
    return NetworkConditionSubscription(**created)


@router.get("/subscriptions/{subscription_id}", response_model=NetworkConditionSubscription)
async def read_subscription(
    subscription_id: str, key: str = Depends(require_api_key)
) -> NetworkConditionSubscription:
    found = await asyncio.to_thread(nc.get, owner_for(key), subscription_id)
    if found is None:
        # Another tenant's subscription and a missing one answer identically.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "no such subscription"},
        )
    return NetworkConditionSubscription(**found)


@router.delete("/subscriptions/{subscription_id}", response_model=NetworkConditionSubscription)
async def remove_subscription(
    subscription_id: str, key: str = Depends(require_api_key)
) -> NetworkConditionSubscription:
    provider = get_live_provider()
    try:
        removed = await asyncio.to_thread(
            nc.delete, owner_for(key), subscription_id, provider
        )
    except nc.NetworkConditionError as exc:
        raise _fail(exc) from None
    return NetworkConditionSubscription(**removed)


@router.post(
    "/subscriptions/{subscription_id}/query", response_model=NetworkConditionQueryResponse
)
async def query_conditions(
    subscription_id: str,
    body: NetworkConditionQueryRequest,
    key: str = Depends(require_api_key),
) -> NetworkConditionQueryResponse:
    """A user action, never a page load. One bounded provider read."""
    provider = get_live_provider()
    try:
        result = await asyncio.to_thread(
            nc.query,
            owner_for(key),
            subscription_id,
            body.phone_number,
            provider,
            body.start,
            body.end,
        )
    except nc.NetworkConditionError as exc:
        raise _fail(exc) from None
    return NetworkConditionQueryResponse(
        subscription_id=subscription_id,
        mode=result.mode,
        intervals=[interval.__dict__ for interval in result.intervals],
        observed_at=result.observed_at,
        provenance=result.provenance,
        empty=result.empty,
    )


@callback_router.post("/callbacks/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def receive_event(
    subscription_id: str,
    body: NetworkConditionEvent,
    authorization: str = Header(default=""),
) -> None:
    """The operator's notification endpoint.

    An unknown subscription and a wrong token are one answer, compared in
    constant time inside `accept_event`. A duplicate is a success: at-least-once
    delivery means the operator will resend, and answering an error to a replay
    only teaches it to keep trying.
    """
    prefix = "Bearer "
    token = authorization[len(prefix) :].strip() if authorization.startswith(prefix) else ""
    try:
        await asyncio.to_thread(
            nc.accept_event,
            subscription_id,
            token,
            body.event_id,
            body.level,
            body.occurred_at,
        )
    except nc.NetworkConditionError as exc:
        raise _fail(exc) from None
