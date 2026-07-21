from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.agent.investigator import build_investigator
from app.api.deps import get_live_provider, require_api_key
from app.chain.models import Verdict
from app.chain.vault import vault
from app.config import settings
from app.consent import ConsentRecord, consents
from app.db import store
from app.domain.schemas import (
    NumberVerificationConsentResponse,
    VerificationRequest,
    VerificationResponse,
)

router = APIRouter(prefix="/v1", tags=["consent"])


def _consent_response(record: ConsentRecord) -> NumberVerificationConsentResponse:
    return NumberVerificationConsentResponse.model_validate(consents.public(record))


def _verification_response(verdict: Verdict, request: VerificationRequest) -> VerificationResponse:
    return VerificationResponse(
        decision=verdict.decision,
        confidence=verdict.confidence,
        hypothesis=verdict.hypothesis,
        reason=verdict.reason,
        chain_id=verdict.chain_id,
        chain=verdict.chain if request.options.return_chain else None,
        evidence_cost=verdict.evidence_cost,
        latency_ms=verdict.latency_ms,
        evidence_steps=len(verdict.chain),
        provider_sources=verdict.provider_sources,
    )


def _consent_unavailable(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": "consent_unavailable", "message": message},
    )


@router.post(
    "/consents/number-verification",
    response_model=NumberVerificationConsentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_number_verification_consent(
    req: VerificationRequest,
    api_key: str = Depends(require_api_key),
) -> NumberVerificationConsentResponse:
    """Create a short-lived Number Verification authorization request."""
    provider = get_live_provider()
    begin = getattr(provider, "begin_number_verification", None)
    if not callable(begin):
        raise _consent_unavailable(
            "Number Verification consent is only available with the NaC provider"
        )

    record = consents.create(
        request=req,
        api_key=api_key,
        redirect_uri=settings.nac_redirect_uri,
        ttl_seconds=settings.nac_consent_ttl_seconds,
    )
    try:
        authorization_url = await begin(
            phone_number=req.phone_number,
            redirect_uri=record.redirect_uri,
            state=record.state,
        )
    except Exception as exc:
        consents.fail(record, "could not create provider authorization request")
        if isinstance(exc, RuntimeError):
            raise _consent_unavailable(str(exc)) from exc
        raise _consent_unavailable("could not create provider authorization request") from exc

    consents.set_authorization_url(record, authorization_url)
    return _consent_response(record)


@router.get(
    "/consents/number-verification/callback",
    response_model=NumberVerificationConsentResponse,
)
async def number_verification_callback(
    state: str = Query(..., min_length=1, max_length=256),
    code: Optional[str] = Query(default=None, min_length=1, max_length=2048),
    error: Optional[str] = Query(default=None, min_length=1, max_length=128),
) -> NumberVerificationConsentResponse:
    """Receive the provider redirect; the authorization code is never exposed."""
    record = consents.by_state(state)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "consent_not_found", "message": "Unknown or expired consent state"},
        )

    if error:
        consents.deny(record)
        return _consent_response(record)

    callback_status = consents.begin_callback(record)
    if callback_status in {"AUTHORIZED", "COMPLETED"}:
        return _consent_response(record)
    if callback_status == "EXPIRED":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "consent_expired", "message": "Consent request expired"},
        )
    if callback_status != "EXCHANGING" or not code:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "consent_callback_in_progress", "message": "Consent callback is already being handled"},
        )

    provider = get_live_provider()
    exchange = getattr(provider, "exchange_number_verification_code", None)
    if not callable(exchange):
        consents.fail(record, "provider does not support Number Verification token exchange")
        raise _consent_unavailable("provider does not support Number Verification token exchange")

    try:
        access_token = await exchange(code=code, redirect_uri=record.redirect_uri)
    except Exception as exc:
        consents.fail(record, "provider token exchange failed")
        if isinstance(exc, RuntimeError):
            raise _consent_unavailable(str(exc)) from exc
        raise _consent_unavailable("provider token exchange failed") from exc

    consents.authorize(record, access_token)
    return _consent_response(record)


@router.get(
    "/consents/{consent_id}",
    response_model=NumberVerificationConsentResponse,
)
async def get_number_verification_consent(
    consent_id: str,
    api_key: str = Depends(require_api_key),
) -> NumberVerificationConsentResponse:
    record = consents.owned(consent_id, api_key)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "consent_not_found", "message": "Consent request not found"},
        )
    return _consent_response(record)


@router.post("/consents/{consent_id}/verify", response_model=VerificationResponse)
async def complete_number_verification(
    consent_id: str,
    api_key: str = Depends(require_api_key),
    console_run_id: Optional[str] = Header(default=None, alias="X-Console-Run-Id"),
) -> VerificationResponse:
    record = consents.owned(consent_id, api_key)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "consent_not_found", "message": "Consent request not found"},
        )

    claim_status, token_or_response = consents.claim_verification(record)
    if claim_status == "COMPLETED" and token_or_response:
        return VerificationResponse.model_validate_json(token_or_response)
    if claim_status == "EXPIRED":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "consent_expired", "message": "Consent request expired"},
        )
    if claim_status != "VERIFYING" or not token_or_response:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "consent_not_ready", "message": f"Consent is {claim_status.lower()}"},
        )

    try:
        investigator = build_investigator(get_live_provider(token_or_response))
        verdict = await investigator.investigate(record.request, run_id=console_run_id)
        store.save(verdict)
        response = _verification_response(verdict, record.request)
        consents.complete(record, response)
        return response
    except Exception as exc:
        consents.fail_verification(record, "verification after consent failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "verification_unavailable", "message": "Verification after consent failed"},
        ) from exc


@router.get("/consents/{consent_id}/verification", tags=["vault"])
async def verify_consent_chain(
    consent_id: str,
    api_key: str = Depends(require_api_key),
) -> dict:
    record = consents.owned(consent_id, api_key)
    if record is None or not record.chain_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "chain_not_found", "message": "No completed verification for consent"},
        )
    chain_record = store.get_record(record.chain_id)
    if chain_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "chain_not_found", "message": f"No chain {record.chain_id}"},
        )
    return {
        "chain_id": record.chain_id,
        "valid": vault.verify(chain_record.verdict_json.encode("utf-8"), chain_record.signature),
        "algorithm": "Ed25519",
        "signature": chain_record.signature,
        "signed_at": chain_record.signed_at,
        "public_key": chain_record.public_key,
    }
