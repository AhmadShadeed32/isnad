from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from app.agent.investigator import build_investigator
from app.api.deps import get_live_provider, require_api_key
from app.api.rate_limit import limit_per_key
from app.chain.models import Verdict
from app.chain.subject import request_commitment
from app.db import store
from app.domain.enums import Decision, Hypothesis
from app.domain.schemas import (
    RequestContext,
    ReverseVerificationRequest,
    ReverseVerificationResponse,
    VerificationRequest,
)
from app.providers.base import EvidenceProvider
from app.registry import evidence as local_evidence

router = APIRouter(prefix="/v1", tags=["reverse"], dependencies=[Depends(limit_per_key)])

# Reverse Isnad verdict vocabulary (internal Decision -> caller-facing trust).
TRUST_MAP = {
    Decision.ALLOW: "TRUST_CALLER",
    Decision.CHALLENGE: "CAUTION",
    Decision.DECLINE: "REJECT_CALLER",
}


async def run_reverse(
    caller_number: str,
    provider: EvidenceProvider,
    run_id: str | None = None,
    callee_number: str | None = None,
    claimed_identity: str = "",
    parallel: bool | None = None,
) -> Verdict:
    """Investigate an inbound caller with the impersonation hypothesis.

    Same engine as forward verification, aimed the other direction: instead of
    the merchant verifying the customer, the caller is verified to the customer.

    Tier 2. Registry and Verified Caller evidence is gathered first because it
    is free and local; the network evidence then runs on top. The two answer
    different questions and neither is sufficient — the registry says whether
    the number belongs to the institution, the network says whether the call is
    really coming from that number. The case this exists to catch is a caller
    wearing the bank's number who is demonstrably not dialling from it, and only
    having both in one chain makes that legible.
    """
    investigator = build_investigator(provider)
    vreq = VerificationRequest(
        phone_number=caller_number,
        context=RequestContext(event="inbound_call"),
    )
    local = await local_evidence.gather(
        caller_number=caller_number,
        callee_number=callee_number,
        claimed_identity=claimed_identity,
    )
    return await investigator.investigate(
        vreq,
        hypothesis_override=Hypothesis.IMPERSONATION,
        run_id=run_id,
        local_evidence=local,
        parallel=parallel,
    )


@router.post("/reverse-verify", response_model=ReverseVerificationResponse)
async def reverse_verify(
    req: ReverseVerificationRequest,
    _key: str = Depends(require_api_key),
    console_run_id: str | None = Header(default=None, alias="X-Console-Run-Id"),
) -> ReverseVerificationResponse:
    """Reverse Isnad: 'Is this caller really who they say they are?'
    -> TRUST_CALLER / CAUTION / REJECT_CALLER with an evidence chain."""
    verdict = await run_reverse(
        req.caller_number,
        get_live_provider(),
        run_id=console_run_id,
        callee_number=req.callee_number,
        claimed_identity=req.claimed_identity,
        parallel=req.options.parallel,
    )
    # The subject of a reverse verdict is the caller being checked, not the
    # customer — that is the number the chain is evidence about.
    await store.save_async(
        verdict,
        subject=req.caller_number,
        request_hash=request_commitment(req),
    )
    return ReverseVerificationResponse(
        trust=TRUST_MAP[verdict.decision],
        chain_grade=verdict.chain_grade,
        confidence=verdict.confidence,
        claimed_identity=req.claimed_identity,
        # verdict.reason verbatim, so the reason shown to a user is the reason
        # the vault signed (S11). It used to be prose built around 120
        # characters of caller-supplied text, which meant the response and the
        # signature disagreed about what the reason was. claimed_identity is
        # already its own field; the caller can render the two together.
        reason=verdict.reason,
        chain_id=verdict.chain_id,
        chain=verdict.chain if req.options.return_chain else None,
    )
