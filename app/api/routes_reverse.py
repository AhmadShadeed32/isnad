from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.agent.investigator import build_investigator
from app.api.deps import get_live_provider, require_api_key
from app.chain.models import Verdict
from app.db import store
from app.domain.enums import Decision, Hypothesis
from app.domain.schemas import (
    RequestContext,
    ReverseVerificationRequest,
    ReverseVerificationResponse,
    VerificationRequest,
)
from app.providers.base import EvidenceProvider

router = APIRouter(prefix="/v1", tags=["reverse"])

# Reverse Isnad verdict vocabulary (internal Decision -> caller-facing trust).
TRUST_MAP = {
    Decision.ALLOW: "TRUST_CALLER",
    Decision.CHALLENGE: "CAUTION",
    Decision.DECLINE: "REJECT_CALLER",
}


async def run_reverse(
    caller_number: str,
    provider: EvidenceProvider,
    run_id: Optional[str] = None,
) -> Verdict:
    """Investigate an inbound caller with the impersonation hypothesis.

    Same engine as forward verification, aimed the other direction: instead of
    the merchant verifying the customer, the caller is verified to the customer.
    """
    investigator = build_investigator(provider)
    vreq = VerificationRequest(
        phone_number=caller_number,
        context=RequestContext(event="inbound_call"),
    )
    return await investigator.investigate(
        vreq,
        hypothesis_override=Hypothesis.IMPERSONATION,
        run_id=run_id,
    )


@router.post("/reverse-verify", response_model=ReverseVerificationResponse)
async def reverse_verify(
    req: ReverseVerificationRequest,
    _key: str = Depends(require_api_key),
    console_run_id: Optional[str] = Header(default=None, alias="X-Console-Run-Id"),
) -> ReverseVerificationResponse:
    """Reverse Isnad: 'Is this caller really who they say they are?'
    -> TRUST_CALLER / CAUTION / REJECT_CALLER with an evidence chain."""
    verdict = await run_reverse(req.caller_number, get_live_provider(), run_id=console_run_id)
    store.save(verdict)
    return ReverseVerificationResponse(
        trust=TRUST_MAP[verdict.decision],
        confidence=verdict.confidence,
        claimed_identity=req.claimed_identity,
        reason=f"Claimed identity: {req.claimed_identity}. {verdict.reason}",
        chain_id=verdict.chain_id,
        chain=verdict.chain if req.options.return_chain else None,
    )
