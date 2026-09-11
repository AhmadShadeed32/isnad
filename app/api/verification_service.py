"""One implementation of "run an investigation and keep the promise about it".

Ownership, the idempotency reservation, persistence and signing used to live
inside `/v1/verify` alone. The judge's paired demonstration needs exactly the
same guarantees — a replay must not buy a second set of operator calls, a key
reused with a different body must be a conflict, and a run that may have
reached the operator must not be quietly retryable — so they live here and both
routes call them. A second copy of this logic is a second set of bugs, and the
one bug it would produce is charging twice for one question.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.agent.investigator import build_engine_for_pricing, build_investigator
from app.cache import CacheUnavailable, cache
from app.chain.models import Verdict
from app.config import settings
from app.db import operations, store
from app.domain.enums import Action
from app.domain.schemas import VerificationRequest, VerificationResponse
from app.policy import counterfactual
from app.presentation import present
from app.providers.base import EvidenceProvider

log = logging.getLogger("isnad")


def idempotency_state_response(state_value: str, request_hash: str) -> VerificationResponse | None:
    """Replay a completed state or reject a conflicting/in-flight one.

    One cache entry changes atomically from ``pending`` to ``done``. Keeping the
    request commitment and response together avoids a capacity eviction opening
    a duplicate-charge window between separate cache keys.
    """
    kind, separator, remainder = state_value.partition(":")
    fingerprint, separator2, payload = remainder.partition(":")
    if not separator or not separator2 or fingerprint != request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_key_reused",
                "message": "Request body differs from the original request",
            },
        )
    if kind == "done":
        try:
            return VerificationResponse.model_validate_json(payload)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "idempotency_state_invalid",
                    "message": "Retry with a new idempotency key",
                },
            ) from exc
    if kind == "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_request_in_progress",
                "message": "Matching request is still processing; retry shortly",
            },
        )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": "idempotency_state_invalid", "message": "Retry with a new idempotency key"},
    )


async def cache_get(key: str) -> str | None:
    """Read the accelerator, off the event loop, and never fatally.

    The cache is not the record any more (R13), so a cache that is missing,
    slow or broken costs a slower answer from the database and nothing else.
    `to_thread` because the Redis client is synchronous: called inline, one
    stalled socket blocked every other request in the process (R14).
    """
    try:
        return await asyncio.to_thread(cache.get, key)
    except CacheUnavailable:
        log.warning("idempotency cache read failed; falling back to the durable record")
        return None


async def cache_set(key: str, value: str) -> None:
    try:
        await asyncio.to_thread(cache.set, key, value, settings.idempotency_ttl_seconds)
    except CacheUnavailable:
        log.warning("idempotency cache write failed; the durable record still holds the mapping")


def response_for(
    verdict: Verdict, req: VerificationRequest, alternative: bool = False
) -> VerificationResponse:
    """One place that turns a Verdict into the wire response.

    Shared by the live path and the durable replay so a replayed answer cannot
    drift from the original in shape — the numbers all come from the immutable
    signed verdict either way.
    """
    return VerificationResponse(
        decision=verdict.decision,
        planner=verdict.planner,
        alternative=(
            counterfactual.compute(verdict, req.phone_number, build_engine_for_pricing())
            if alternative
            else None
        ),
        chain_grade=verdict.chain_grade,
        confidence=verdict.confidence,
        hypothesis=verdict.hypothesis,
        reason=verdict.reason,
        chain_id=verdict.chain_id,
        chain=verdict.chain if req.options.return_chain else None,
        evidence_cost=verdict.evidence_cost,
        latency_ms=verdict.latency_ms,
        evidence_steps=len(verdict.chain),
        provider_sources=verdict.provider_sources,
        presentation=present(verdict),
    )


async def replay_or_refuse(
    existing: operations.Operation, request_hash: str, req: VerificationRequest
) -> VerificationResponse:
    """Answer a key that is already reserved, without spending anything.

    Four outcomes, and the ordering matters. A body mismatch is checked first:
    a key reused against a *different* request is a caller bug, and answering
    it with the earlier result would be worse than refusing it. On the judge's
    paired path the evidence source is inside the commitment, so replaying a
    mock key in real mode lands here as a conflict rather than as a mock result
    wearing a real label.
    """
    if not secrets.compare_digest(existing.request_hash, request_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_key_reused",
                "message": "This Idempotency-Key was used with a different request body",
            },
        )
    if existing.state == operations.DONE and existing.chain_id:
        verdict = await store.get_async(existing.chain_id)
        if verdict is not None:
            # Rebuilt from the signed chain, not from a cached copy of the
            # response. This is the path a restart takes, and it is the reason
            # the mapping is a row: the original answer is still reachable
            # after the cache that held it is gone.
            return response_for(verdict, req, alternative=True)
        # `done` with a chain that is not readable by this owner or no longer
        # exists. Refusing is the only safe answer: the work was performed.
    if existing.is_orphaned() or existing.state == operations.UNCERTAIN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_reconciliation_required",
                "message": (
                    "A previous attempt with this key may have completed provider work. "
                    "Retry with a new Idempotency-Key after reconciling."
                ),
            },
        )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "idempotency_request_in_progress",
            "message": "Matching request is still processing; retry shortly",
        },
    )


@dataclass
class Investigation:
    """What running one investigation produced.

    `replayed` is True when the key was already answered and nothing was spent.
    `response` is set either way; `verdict` only on a fresh run.
    """

    verdict: Verdict | None
    response: VerificationResponse
    replayed: bool
    cache_key: str | None
    request_hash: str


async def execute(
    *,
    req: VerificationRequest,
    owner: str,
    request_hash: str,
    provider: EvidenceProvider,
    idempotency_key: str | None = None,
    run_id: str | None = None,
    planner=None,
    available_actions: set[Action] | None = None,
    parallel: bool | None = None,
    stamp: Callable[[Verdict], None] | None = None,
    investigator_factory: Callable[[EvidenceProvider], object] | None = None,
    response_builder: Callable[[Verdict, VerificationRequest], VerificationResponse] | None = None,
) -> Investigation:
    """Reserve, investigate, sign and persist — or answer a key already spent.

    `stamp` runs after the verdict exists and before it is signed, which is the
    only window in which provenance can become part of the signed bytes rather
    than a label beside them.

    `investigator_factory` and `response_builder` exist because building the
    response is *inside* the reservation's try block, not after it: a failure
    between signing and answering leaves a key that may have bought operator
    calls, and it has to be marked for reconciliation like any other. Callers
    pass their own so the route module stays the seam those cases are pinned
    through.
    """
    owner_key = operations.key_digest(idempotency_key) if idempotency_key else None
    # The key is hashed, not embedded, in both stores. In memory the plaintext
    # was harmless, but under the Redis backend a cache key is written into
    # KEYS, MONITOR output and RDB snapshots — that is a credential on disk
    # (S12) — and the durable row outlives the request entirely.
    cache_key = f"idem:{owner}:{owner_key}" if owner_key else None
    reserved = False
    work_started = False
    if owner_key:
        # The cache first, because it is the fast path and, under Redis, the
        # cross-replica one. It is never the authority: a miss here falls
        # through to the row, which survives a restart.
        state_value = await cache_get(cache_key)
        if state_value is not None:
            replayed = idempotency_state_response(state_value, request_hash)
            if replayed is not None:
                return Investigation(None, replayed, True, cache_key, request_hash)
        existing = await operations.reserve_async(owner, owner_key, request_hash)
        if existing is not None:
            return Investigation(
                None,
                await replay_or_refuse(existing, request_hash, req),
                True,
                cache_key,
                request_hash,
            )
        reserved = True
    try:
        build = investigator_factory or (lambda p: build_investigator(p, planner=planner))
        investigator = build(provider)
        # Past this line a provider call may have been made, so the reservation
        # can no longer be released on failure: see the `except` below.
        work_started = True
        verdict = await investigator.investigate(
            req, run_id=run_id, parallel=parallel, available_actions=available_actions
        )
        if stamp is not None:
            stamp(verdict)
        # The chain and the key->chain mapping commit together (R13).
        await store.save_async(
            verdict,
            subject=req.phone_number,
            request_hash=request_hash,
            operation=(owner, owner_key) if owner_key else None,
        )
        build_response = response_builder or (
            lambda v, r: response_for(v, r, alternative=True)
        )
        return Investigation(verdict, build_response(verdict, req), False, cache_key, request_hash)
    except BaseException:
        # `BaseException`, so a cancelled request is covered: cancellation was
        # one of the three ways this window used to lose the mapping.
        if reserved:
            if work_started:
                # Something may have reached the operator and this service
                # cannot prove otherwise. The key stays spent and a retry is
                # refused for reconciliation, because the alternative is
                # charging the merchant twice for one question.
                await operations.mark_uncertain_async(owner, owner_key)
            else:
                # Nothing had been attempted yet, so the key is genuinely free.
                await operations.release_async(owner, owner_key)
        raise


async def remember(result: Investigation) -> None:
    """Accelerate the next replay. Never the record.

    The mapping is already durable by the time this runs, so a failure here
    costs a slower replay, never a second charge — which is exactly what it used
    to cost.
    """
    if result.cache_key and not result.replayed:
        await cache_set(
            result.cache_key, f"done:{result.request_hash}:{result.response.model_dump_json()}"
        )
