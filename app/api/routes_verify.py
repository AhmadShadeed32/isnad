from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.agent import explain
from app.agent.investigator import build_engine_for_pricing, build_investigator
from app.api.deps import get_live_provider, require_api_key
from app.api.rate_limit import limit_per_key
from app.cache import CacheCapacityExceeded, cache
from app.chain import subject
from app.chain.vault import vault
from app.config import settings
from app.db import store
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
    # The key is hashed, not embedded. In memory the plaintext was harmless,
    # but under the Redis backend a cache key is written into KEYS, MONITOR
    # output and RDB snapshots — that is a credential on disk (S12).
    cache_key = f"idem:{owner_hash(_key)}:{idempotency_key}" if idempotency_key else None
    reservation_key = cache_key
    reservation_value: str | None = None
    reservation_completed = False
    if cache_key:
        state_value = cache.get(cache_key)
        if state_value is not None:
            response = _idempotency_state_response(state_value, request_hash)
            if response is not None:
                return response
        # Reserve before starting paid evidence. `set_if_absent` is a lock in
        # memory and SET NX in Redis, so two concurrent retries cannot both
        # investigate and charge while they race through a get/set pair.
        reservation_value = f"pending:{request_hash}:{uuid.uuid4().hex}"
        try:
            owns_reservation = cache.set_if_absent(
                cache_key, reservation_value, settings.idempotency_ttl_seconds
            )
        except CacheCapacityExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "idempotency_capacity_exceeded", "message": "Retry shortly"},
            ) from exc
        if not owns_reservation:
            state_value = cache.get(cache_key)
            if state_value is not None:
                response = _idempotency_state_response(state_value, request_hash)
                if response is not None:
                    return response
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "idempotency_request_in_progress",
                    "message": "Matching request is still processing; retry shortly",
                },
            )
    try:
        investigator = build_investigator(get_live_provider())
        verdict = await investigator.investigate(
            req, run_id=console_run_id, parallel=req.options.parallel
        )
        await store.save_async(verdict, subject=req.phone_number, request_hash=request_hash)
        response = VerificationResponse(
            decision=verdict.decision,
            planner=verdict.planner,
            alternative=counterfactual.compute(
                verdict, req.phone_number, build_engine_for_pricing()
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
        if cache_key:
            cache.set(
                cache_key,
                f"done:{request_hash}:{response.model_dump_json()}",
                settings.idempotency_ttl_seconds,
            )
            reservation_completed = True
        return response
    finally:
        if reservation_key and reservation_value and not reservation_completed:
            cache.delete_if_value(reservation_key, reservation_value)


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
