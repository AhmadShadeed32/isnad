from __future__ import annotations

import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.agent.investigator import build_investigator
from app.api.deps import get_live_provider, require_api_key
from app.cache import cache
from app.chain.vault import vault
from app.config import settings
from app.db import store
from app.domain.schemas import VerificationRequest, VerificationResponse

router = APIRouter(prefix="/v1", tags=["verify"])


@router.post("/verify", response_model=VerificationResponse)
async def verify(
    req: VerificationRequest,
    _key: str = Depends(require_api_key),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    console_run_id: Optional[str] = Header(default=None, alias="X-Console-Run-Id"),
) -> VerificationResponse:
    """The one call: 'Can I trust this interaction?' -> ALLOW / CHALLENGE / DECLINE
    with a full evidence chain attached.

    Supports `Idempotency-Key`: retrying with the same key returns the original
    verdict instead of re-investigating (and re-charging CAMARA calls)."""
    cache_key = f"idem:{_key}:{idempotency_key}" if idempotency_key else None
    if cache_key:
        request_hash = hashlib.sha256(req.model_dump_json().encode("utf-8")).hexdigest()
        stored_hash = cache.get(f"{cache_key}:request")
        if stored_hash is not None and stored_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "idempotency_key_reused", "message": "Request body differs from the original request"},
            )
        cached = cache.get(cache_key)
        if cached is not None:
            return VerificationResponse.model_validate_json(cached)

    investigator = build_investigator(get_live_provider())
    verdict = await investigator.investigate(req, run_id=console_run_id)
    store.save(verdict)
    response = VerificationResponse(
        decision=verdict.decision,
        confidence=verdict.confidence,
        hypothesis=verdict.hypothesis,
        reason=verdict.reason,
        chain_id=verdict.chain_id,
        chain=verdict.chain if req.options.return_chain else None,
        evidence_cost=verdict.evidence_cost,
        latency_ms=verdict.latency_ms,
        evidence_steps=len(verdict.chain),
        provider_sources=verdict.provider_sources,
    )
    if cache_key:
        cache.set(f"{cache_key}:request", request_hash, settings.idempotency_ttl_seconds)
        cache.set(cache_key, response.model_dump_json(), settings.idempotency_ttl_seconds)
    return response


@router.get("/chains/{chain_id}", response_model=VerificationResponse)
async def get_chain(chain_id: str, _key: str = Depends(require_api_key)) -> VerificationResponse:
    """Replayable evidence — for COD dispute / chargeback resolution."""
    verdict = store.get(chain_id)
    if verdict is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "chain_not_found", "message": f"No chain {chain_id}"},
        )
    return VerificationResponse(
        decision=verdict.decision,
        confidence=verdict.confidence,
        hypothesis=verdict.hypothesis,
        reason=verdict.reason,
        chain_id=verdict.chain_id,
        chain=verdict.chain,
        evidence_cost=verdict.evidence_cost,
        latency_ms=verdict.latency_ms,
        evidence_steps=len(verdict.chain),
        provider_sources=verdict.provider_sources,
    )


@router.get("/chains/{chain_id}/verification", tags=["vault"])
async def verify_chain(chain_id: str, _key: str = Depends(require_api_key)) -> dict:
    """Evidence-vault check: recompute the signature over the stored chain and
    confirm it hasn't been tampered with. Used to settle COD disputes."""
    rec = store.get_record(chain_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "chain_not_found", "message": f"No chain {chain_id}"},
        )
    return {
        "chain_id": chain_id,
        "valid": vault.verify(rec.verdict_json.encode("utf-8"), rec.signature),
        "algorithm": "Ed25519",
        "signature": rec.signature,
        "signed_at": rec.signed_at,
        "public_key": rec.public_key,
    }


@router.get("/vault/public-key", tags=["vault"])
async def vault_public_key() -> dict:
    """The public key anyone can use to independently verify a chain signature."""
    return {"algorithm": "Ed25519", "public_key": vault.public_key_hex()}
