from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.agent.investigator import build_engine_for_pricing, build_investigator
from app.api.content_negotiation import accept_quality, prefers_html
from app.api.deps import get_live_provider, require_api_key
from app.api.rate_limit import limit_per_ip, limit_per_key
from app.chain.models import Verdict
from app.chain.vault import vault
from app.config import settings
from app.consent import ConsentCapacityExceeded, ConsentRecord, consents
from app.db import store
from app.domain.enums import Action
from app.domain.schemas import (
    NumberVerificationConsentResponse,
    VerificationRequest,
    VerificationResponse,
)
from app.policy import counterfactual
from app.presentation import present

router = APIRouter(prefix="/v1", tags=["consent"], dependencies=[Depends(limit_per_key)])
# No /v1 prefix: this is a browser-facing landing page, not the JSON API —
# same split as routes_judge.page_router / routes_console.page_router.
page_router = APIRouter(tags=["consent"], dependencies=[Depends(limit_per_ip)])

_CONSENT_COMPLETE_HTML = Path(__file__).parent.parent / "static" / "consent_complete.html"


# Extracted to app/api/content_negotiation.py so the I13 proof-share route
# uses the same implementation rather than a second copy of it.
_accept_quality = accept_quality
_prefers_html = prefers_html


def _redirect_to_completion_page() -> RedirectResponse:
    return RedirectResponse(
        url="/consent/complete",
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"Vary": "Accept", "Cache-Control": "no-store"},
    )


@page_router.get("/consent/complete", response_class=HTMLResponse, include_in_schema=False)
async def consent_complete_page() -> HTMLResponse:
    """Generic same-origin landing page for a subscriber's phone browser.

    Carries no code, state, phone number, consent ID or provider error text —
    everything the callback learned about this specific attempt stays
    server-side (see number_verification_callback's HTML branch below).
    """
    html = _CONSENT_COMPLETE_HTML.read_text(encoding="utf-8")
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


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
        planner=verdict.planner,
        chain_grade=verdict.chain_grade,
        alternative=counterfactual.compute(
            verdict, request.phone_number, build_engine_for_pricing()
        ),
        presentation=present(verdict),
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

    try:
        record = consents.create(
            request=req,
            api_key=api_key,
            redirect_uri=settings.nac_redirect_uri,
            ttl_seconds=settings.nac_consent_ttl_seconds,
        )
    except ConsentCapacityExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "consent_capacity_exceeded",
                "message": "Too many active consent requests; try again later",
            },
        ) from exc
    try:
        authorization_url = await begin(
            phone_number=req.phone_number,
            redirect_uri=record.redirect_uri,
            state=record.state,
            nonce=record.nonce,
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
    response_model=None,
)
async def number_verification_callback(
    state: str = Query(..., min_length=1, max_length=256),
    code: str | None = Query(default=None, min_length=1, max_length=2048),
    error: str | None = Query(default=None, min_length=1, max_length=128),
    accept: str | None = Header(default=None),
) -> NumberVerificationConsentResponse | RedirectResponse:
    """Receive the provider redirect; the authorization code is never exposed.

    A browser navigating here directly (Accept prefers text/html) is bounced
    to the generic /consent/complete page instead of seeing raw JSON or an
    error naming the provider/consent state — for every outcome, not only
    success (P4a step 8). All the same state transitions below run first;
    only the *response representation* differs.
    """
    prefer_html = _prefers_html(accept)

    def respond(record_for_json: ConsentRecord) -> NumberVerificationConsentResponse | RedirectResponse:
        if prefer_html:
            return _redirect_to_completion_page()
        return _consent_response(record_for_json)

    record = consents.by_state(state)
    if record is None:
        if prefer_html:
            return _redirect_to_completion_page()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "consent_not_found", "message": "Unknown or expired consent state"},
        )

    if error:
        consents.deny(record)
        return respond(record)

    callback_status = consents.begin_callback(record)
    if callback_status in {"AUTHORIZED", "COMPLETED"}:
        return respond(record)
    if callback_status == "EXPIRED":
        if prefer_html:
            return _redirect_to_completion_page()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "consent_expired", "message": "Consent request expired"},
        )
    if callback_status == consents.REPLAYED:
        if prefer_html:
            return _redirect_to_completion_page()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "consent_callback_in_progress",
                "message": "Consent callback is already being handled",
            },
        )
    if callback_status != "EXCHANGING" or not code:
        if prefer_html:
            return _redirect_to_completion_page()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "consent_callback_in_progress",
                "message": "Consent callback is already being handled",
            },
        )

    provider = get_live_provider()
    exchange = getattr(provider, "exchange_number_verification_code", None)
    if not callable(exchange):
        consents.fail(record, "provider does not support Number Verification token exchange")
        if prefer_html:
            return _redirect_to_completion_page()
        raise _consent_unavailable("provider does not support Number Verification token exchange")

    try:
        access_token = await exchange(
            code=code, redirect_uri=record.redirect_uri, nonce=record.nonce
        )
    except Exception as exc:
        consents.fail(record, "provider token exchange failed")
        if prefer_html:
            return _redirect_to_completion_page()
        if isinstance(exc, RuntimeError):
            raise _consent_unavailable(str(exc)) from exc
        raise _consent_unavailable("provider token exchange failed") from exc

    consents.authorize(record, access_token)
    return respond(record)


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
    console_run_id: str | None = Header(default=None, alias="X-Console-Run-Id"),
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
        verdict = await investigator.investigate(
            record.request,
            run_id=console_run_id,
            required_action=Action.NUMBER_VERIFY,
        )
        await store.save_async(
            verdict,
            subject=record.request.phone_number,
            # The commitment frozen at consent creation (app/consent.py), not
            # recomputed here — the receipt must attest to what the merchant
            # actually asked for at approval time, not to `record.request` as
            # it happens to read now.
            request_hash=record.request_hash,
        )
        response = _verification_response(verdict, record.request)
        consents.complete(record, response)
        return response
    except Exception as exc:
        consents.fail_verification(record, "verification after consent failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "verification_unavailable",
                "message": "Verification after consent failed",
            },
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
    chain_record = await store.get_record_async(record.chain_id)
    if chain_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "chain_not_found", "message": "No such chain"},
        )
    return {
        "chain_id": record.chain_id,
        "valid": vault.verify_with(
            chain_record.public_key,
            chain_record.verdict_json.encode("utf-8"),
            chain_record.signature,
        ),
        "algorithm": "Ed25519",
        "signature": chain_record.signature,
        "signed_at": chain_record.signed_at,
        "public_key": chain_record.public_key,
    }
