from __future__ import annotations

import asyncio
import logging
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.agent import explain
from app.agent.investigator import build_engine_for_pricing, build_investigator
from app.api.deps import get_live_provider, require_api_key
from app.api.rate_limit import limit_per_key
from app.cache import CacheUnavailable, cache
from app.chain import subject
from app.chain.vault import vault
from app.config import settings
from app.db import operations, store
from app.domain.schemas import (
    ExplainRequest,
    ExplainResponse,
    SubjectCheckRequest,
    VerificationRequest,
    VerificationResponse,
)
from app.ownership import owner_hash
from app.policy import counterfactual
from app.presentation import present

log = logging.getLogger("isnad")

router = APIRouter(
    prefix="/v1",
    tags=["verify"],
    # Per key: these cost money on the nac path (S12).
    dependencies=[Depends(limit_per_key)],
)


def _idempotency_state_response(state_value: str, request_hash: str) -> VerificationResponse | None:
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


async def _cache_get(key: str) -> str | None:
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


async def _cache_set(key: str, value: str) -> None:
    try:
        await asyncio.to_thread(cache.set, key, value, settings.idempotency_ttl_seconds)
    except CacheUnavailable:
        log.warning("idempotency cache write failed; the durable record still holds the mapping")


async def _replay_or_refuse(
    existing: operations.Operation, request_hash: str, req: VerificationRequest
) -> VerificationResponse:
    """Answer a key that is already reserved, without spending anything.

    Four outcomes, and the ordering matters. A body mismatch is checked first:
    a key reused against a *different* request is a caller bug, and answering
    it with the earlier result would be worse than refusing it.
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
            return _response_for(verdict, req, alternative=True)
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


def _response_for(
    verdict, req: VerificationRequest, alternative: bool = False
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


@router.post("/verify", response_model=VerificationResponse)
async def verify(
    req: VerificationRequest,
    _key: str = Depends(require_api_key),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    console_run_id: str | None = Header(default=None, alias="X-Console-Run-Id"),
) -> VerificationResponse:
    """The one call: 'Can I trust this interaction?' -> ALLOW / CHALLENGE / DECLINE
    with a full evidence chain attached.

    Supports `Idempotency-Key`: retrying with the same key returns the original
    verdict instead of re-investigating (and re-charging CAMARA calls)."""
    # Computed unconditionally: it is the idempotency guard's comparison value
    # *and* part of what the verdict binds to when it is signed (S5). This is a
    # keyed commitment, not bare SHA-256: receipts are public and predictable
    # request bodies otherwise make the signed digest an offline PII oracle.
    request_hash = subject.request_commitment(req)
    owner = owner_hash(_key)
    # The key is hashed, not embedded, in both stores. In memory the plaintext
    # was harmless, but under the Redis backend a cache key is written into
    # KEYS, MONITOR output and RDB snapshots — that is a credential on disk
    # (S12) — and the durable row outlives the request entirely.
    key_hash = operations.key_digest(idempotency_key) if idempotency_key else None
    cache_key = f"idem:{owner}:{key_hash}" if key_hash else None
    reserved = False
    work_started = False
    if key_hash:
        # The cache first, because it is the fast path and, under Redis, the
        # cross-replica one. It is never the authority: a miss here falls
        # through to the row, which survives a restart.
        state_value = await _cache_get(cache_key)
        if state_value is not None:
            response = _idempotency_state_response(state_value, request_hash)
            if response is not None:
                return response
        existing = await operations.reserve_async(owner, key_hash, request_hash)
        if existing is not None:
            return await _replay_or_refuse(existing, request_hash, req)
        reserved = True
    try:
        investigator = build_investigator(get_live_provider())
        # Past this line a provider call may have been made, so the reservation
        # can no longer be released on failure: see the `except` below.
        work_started = True
        verdict = await investigator.investigate(
            req, run_id=console_run_id, parallel=req.options.parallel
        )
        # The chain and the key->chain mapping commit together (R13).
        await store.save_async(
            verdict,
            subject=req.phone_number,
            request_hash=request_hash,
            operation=(owner, key_hash) if key_hash else None,
        )
        response = _response_for(verdict, req, alternative=True)
        if cache_key:
            # Acceleration only. The mapping is already durable at this point,
            # so a failure here costs a slower replay, never a second charge —
            # which is exactly what it used to cost.
            await _cache_set(cache_key, f"done:{request_hash}:{response.model_dump_json()}")
        return response
    except BaseException:
        # `BaseException`, so a cancelled request is covered: cancellation was
        # one of the three ways this window used to lose the mapping.
        if reserved:
            if work_started:
                # Something may have reached the operator and this service
                # cannot prove otherwise. The key stays spent and a retry is
                # refused for reconciliation, because the alternative is
                # charging the merchant twice for one question.
                await operations.mark_uncertain_async(owner, key_hash)
            else:
                # Nothing had been attempted yet, so the key is genuinely free.
                await operations.release_async(owner, key_hash)
        raise


@router.get("/chains/{chain_id}", response_model=VerificationResponse)
async def get_chain(chain_id: str, _key: str = Depends(require_api_key)) -> VerificationResponse:
    """Replayable evidence — for COD dispute / chargeback resolution."""
    verdict = await store.get_async(chain_id)
    if verdict is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            # A constant, not the path parameter. It used to be reflected into
            # a message the console threw and injected into the DOM (S10).
            detail={"code": "chain_not_found", "message": "No such chain"},
        )
    return VerificationResponse(
        decision=verdict.decision,
        planner=verdict.planner,
        chain_grade=verdict.chain_grade,
        confidence=verdict.confidence,
        hypothesis=verdict.hypothesis,
        reason=verdict.reason,
        chain_id=verdict.chain_id,
        chain=verdict.chain,
        evidence_cost=verdict.evidence_cost,
        latency_ms=verdict.latency_ms,
        evidence_steps=len(verdict.chain),
        provider_sources=verdict.provider_sources,
        # Recomputed fresh from the immutable stored Verdict every read, never
        # cached: present() reads only verdict.policy_snapshot (frozen at
        # signing time), never the live engine, so this can never silently
        # replay an old chain against today's policy (P2).
        presentation=present(verdict),
    )


@router.get("/chains/{chain_id}/verification", tags=["vault"])
async def verify_chain(chain_id: str, _key: str = Depends(require_api_key)) -> dict:
    """Evidence-vault check: recompute the signature over the stored chain and
    confirm it hasn't been tampered with. Used to settle COD disputes."""
    rec = await store.get_record_async(chain_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            # A constant, not the path parameter. It used to be reflected into
            # a message the console threw and injected into the DOM (S10).
            detail={"code": "chain_not_found", "message": "No such chain"},
        )
    return {
        "chain_id": chain_id,
        # Against the key that actually signed this record, not against whatever
        # key this process happens to be holding (S6) — and only if that key is
        # one this deployment trusts, or a forged row could bring its own.
        "valid": vault.verify_with(rec.public_key, rec.verdict_json.encode("utf-8"), rec.signature),
        "key_trusted": vault.trusts(rec.public_key),
        "algorithm": "Ed25519",
        "signature": rec.signature,
        # Read from inside the signed payload, not from the sibling column it
        # used to live in — as a column it could be backdated without breaking
        # verification (S5).
        "signed_at": rec.verdict.signed_at or rec.signed_at,
        "public_key": rec.public_key,
    }


@router.post("/chains/{chain_id}/explain", response_model=ExplainResponse, tags=["agent"])
async def explain_chain(
    chain_id: str,
    body: ExplainRequest,
    _key: str = Depends(require_api_key),
) -> ExplainResponse:
    """Ask the agent about a decision it already made (T4).

    Grounded in the stored chain: the prompt is built from the structured links —
    action, signal, result, delta — never from free text (T3's boundary). The
    question is untrusted, capped at 280 characters by the schema, and the model
    is told it cannot change any verdict. Nothing here writes to the chain, and
    the route is rate limited per key like every other billable route.
    """
    verdict = await store.get_async(chain_id)
    if verdict is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "chain_not_found", "message": "No such chain"},
        )
    try:
        answer = await asyncio.to_thread(explain.answer, verdict, body.question)
    except explain.ExplainUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "explain_unavailable", "message": str(exc)},
        ) from exc
    except Exception as exc:  # a model failure must not look like a chain failure
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "explain_failed", "message": "Could not answer right now"},
        ) from exc
    return ExplainResponse(chain_id=chain_id, question=body.question, answer=answer)


@router.post("/chains/{chain_id}/verification", tags=["vault"])
async def verify_chain_subject(
    chain_id: str,
    body: SubjectCheckRequest,
    _key: str = Depends(require_api_key),
) -> dict:
    """Settle a dispute: is this chain evidence about *this* number?

    The signature alone never answered that. Before S5 the signed payload held no
    subject, so a merchant could present a clean ALLOW chain obtained for any
    other number and it verified — the core value proposition failing open.

    The number is hashed under the server pepper and compared against the binding
    inside the signed bytes. It is not stored and not echoed back.
    """
    rec = await store.get_record_async(chain_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "chain_not_found", "message": "No such chain"},
        )
    signature_valid = vault.verify_with(
        rec.public_key, rec.verdict_json.encode("utf-8"), rec.signature
    )
    return {
        "chain_id": chain_id,
        "valid": signature_valid,
        "subject_match": signature_valid
        and subject.matches(rec.verdict.subject_hash, body.phone_number),
        "bound": bool(rec.verdict.subject_hash),
        "algorithm": "Ed25519",
        "signed_at": rec.verdict.signed_at or rec.signed_at,
    }


@router.get("/vault/public-key", tags=["vault"])
async def vault_public_key() -> dict:
    """The public key anyone can use to independently verify a chain signature."""
    return {"algorithm": "Ed25519", "public_key": vault.public_key_hex()}
