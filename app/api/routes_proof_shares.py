from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.content_negotiation import prefers_html
from app.api.deps import require_api_key
from app.api.rate_limit import limit_per_ip, limit_per_key
from app.chain.subject import idempotency_fingerprint
from app.config import settings
from app.db import proof_shares, store
from app.domain.schemas import ProofShareCreateRequest, ProofShareCreateResponse

router = APIRouter(prefix="/v1", tags=["proof-shares"], dependencies=[Depends(limit_per_key)])
# No /v1 prefix, no auth: the bearer token in the path IS the credential.
page_router = APIRouter(tags=["proof-shares"], dependencies=[Depends(limit_per_ip)])

_PROOF_HTML = Path(__file__).parent.parent / "static" / "proof.html"

_CHAIN_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "chain_not_found", "message": "No such chain"},
)
_SHARE_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "share_not_found", "message": "No such proof share"},
)


def _idempotency_key(
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=128),
) -> str:
    return idempotency_key


@router.post(
    "/chains/{chain_id}/proof-shares",
    response_model=ProofShareCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_proof_share(
    chain_id: str,
    body: ProofShareCreateRequest,
    _key: str = Depends(require_api_key),
    idempotency_key: str = Depends(_idempotency_key),
) -> ProofShareCreateResponse:
    rec = await store.get_record_async(chain_id)
    if rec is None:
        raise _CHAIN_NOT_FOUND

    ttl_seconds = body.ttl_seconds or settings.proof_share_default_ttl_seconds
    if ttl_seconds > settings.proof_share_max_ttl_seconds:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "ttl_too_long", "message": "ttl_seconds exceeds the configured maximum"},
        )

    fingerprint = idempotency_fingerprint("proof_share.create", chain_id, body=body)
    try:
        outcome = await asyncio.to_thread(
            proof_shares.create_share,
            chain_id=chain_id,
            purpose=body.purpose,
            ttl_seconds=ttl_seconds,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
    except proof_shares.IdempotencyKeyConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_key_reused",
                "message": "Idempotency-Key was already used for a different request",
            },
        ) from exc
    return ProofShareCreateResponse(**outcome.response)


@router.delete("/chains/{chain_id}/proof-shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_proof_share(
    chain_id: str,
    share_id: str,
    _key: str = Depends(require_api_key),
) -> Response:
    rec = await store.get_record_async(chain_id)
    if rec is None:
        raise _CHAIN_NOT_FOUND
    found = await asyncio.to_thread(proof_shares.revoke_share, chain_id=chain_id, share_id=share_id)
    if not found:
        raise _SHARE_NOT_FOUND
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@page_router.get("/p/{token}")
async def read_proof_share(
    token: str, request: Request, accept: str | None = Header(default=None)
) -> Response:
    """Public, bounded, unauthenticated by design: the token in the path IS
    the credential. Missing, expired and revoked all answer identically, so
    a reader learns nothing about which one it was.

    A browser navigating here gets the page, which verifies the attestation
    signature itself with WebCrypto; a script/curl client gets the JSON.
    Same content negotiation as P4a's consent callback (`prefers_html`):
    JSON stays the default, and only an explicit, strictly-higher `text/html`
    preference switches — so an `Accept:`-less client is never surprised.
    """
    headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
    if prefers_html(accept):
        # The page fetches the JSON for itself; rendering it server-side would
        # mean trusting the server's own rendering of a thing whose entire
        # value is that the reader can check it independently.
        return HTMLResponse(
            _PROOF_HTML.read_text(encoding="utf-8"), status_code=status.HTTP_200_OK, headers=headers
        )

    attestation = await asyncio.to_thread(proof_shares.resolve_attestation, token)
    if attestation is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"code": "share_unavailable", "message": "This link is not available"},
            headers=headers,
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content=attestation, headers=headers)
