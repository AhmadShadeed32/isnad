from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.agent import explain
from app.agent.investigator import build_investigator
from app.api import verification_service
from app.api.deps import get_live_provider, require_api_key, require_read_access
from app.api.rate_limit import limit_per_key
from app.chain import subject
from app.chain.vault import vault
from app.db import store
from app.domain.schemas import (
    ExplainRequest,
    ExplainResponse,
    SubjectCheckRequest,
    VerificationRequest,
    VerificationResponse,
)
from app.ownership import owner_hash
from app.presentation import present

log = logging.getLogger("isnad")

router = APIRouter(
    prefix="/v1",
    tags=["verify"],
    # Per key: these cost money on the nac path (S12).
    dependencies=[Depends(limit_per_key)],
)


# Ownership, idempotency, persistence and signing live in one place, shared with
# the judge's paired-source route: app/api/verification_service.py. These names
# are kept as thin aliases because the tests that pin this route's semantics
# reach for them, and because a reader following `/v1/verify` should still be
# able to see what it does without a second file open.
_idempotency_state_response = verification_service.idempotency_state_response
_cache_get = verification_service.cache_get
_cache_set = verification_service.cache_set
_replay_or_refuse = verification_service.replay_or_refuse
_response_for = verification_service.response_for


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
    result = await verification_service.execute(
        req=req,
        owner=owner,
        request_hash=request_hash,
        provider=get_live_provider(),
        idempotency_key=idempotency_key,
        run_id=console_run_id,
        parallel=req.options.parallel,
        # Resolved from this module at call time, not captured at import: these
        # two names are the seam the concurrency and reconciliation regressions
        # replace, and they must keep meaning what this route does.
        investigator_factory=lambda provider: build_investigator(provider),
        response_builder=lambda verdict, request: _response_for(
            verdict, request, alternative=True
        ),
    )
    await verification_service.remember(result)
    return result.response


@router.get("/chains/{chain_id}", response_model=VerificationResponse)
async def get_chain(chain_id: str, _owner: str = Depends(require_read_access)) -> VerificationResponse:
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
async def verify_chain(chain_id: str, _owner: str = Depends(require_read_access)) -> dict:
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
