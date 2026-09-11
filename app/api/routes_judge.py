"""Judge page and scoped, bounded paired Nokia demonstration endpoints."""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.agent.investigator import build_engine_for_pricing
from app.agent.planner import GreedyPlanner, LLMPlanner
from app.api import demo_token, verification_service
from app.api.deps import require_judge_session
from app.api.rate_limit import limit_per_ip, limit_per_key
from app.chain import subject
from app.config import makes_billable_calls, settings
from app.judge import evidence
from app.judge.access import (
    SESSION_HEADER,
    AllowanceExhausted,
    JudgeAccessError,
    JudgeApiKey,
    JudgeSession,
)
from app.judge.access import access as judge_access
from app.judge.evidence import EvidenceSource, JudgePlanner
from app.judge.schemas import JudgeRunCommitment, JudgeRunRequest
from app.providers import nac_contract
from app.ui import page_path

# Annotated rather than a plain default: FastAPI's recommended form, and the one
# that does not read as a mutable default argument.
JudgeSessionDep = Annotated[JudgeSession, Depends(require_judge_session)]

# A render mints a short-lived demo credential, so Judge Mode has the same
# address-level page limit as the full console.  It is not a free token-minting
# endpoint for a refresh loop.
page_router = APIRouter(tags=["judge"], dependencies=[Depends(limit_per_ip)])

_JUDGE_HTML = page_path("judge")
_API_KEYS_HTML = page_path("api_keys")
_TOKEN_PLACEHOLDER = "__ISNAD_JUDGE_TOKEN__"


@page_router.get("/judge", response_class=HTMLResponse, include_in_schema=False)
async def judge_page() -> HTMLResponse:
    """Serve the on-stage checkout journey with a short-lived demo token.

    This uses the same minting policy as ``/console``: no credential is put in
    a production render, and a demo render receives a fresh token that expires
    server-side.  It is also explicitly non-cacheable because the page body can
    contain that token.
    """
    token = demo_token.mint() if settings.demo_mode else ""
    html = _JUDGE_HTML.read_text(encoding="utf-8").replace(_TOKEN_PLACEHOLDER, token)
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


@page_router.get("/api-keys", response_class=HTMLResponse, include_in_schema=False)
async def api_keys_page() -> HTMLResponse:
    """Where a judge mints a merchant key and is shown how to call the API.

    No credential is rendered into this page, not even a demo token: the key
    the page exists to issue is minted by an authenticated request after the
    access code has been entered, and is shown once.
    """
    return HTMLResponse(
        content=_API_KEYS_HTML.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store"},
    )


# --- the paired evidence-source demonstration -------------------------------
#
# The page above is still read-only. What follows is the ONE narrow mutation
# entry point a judge has, and every guarantee `/v1/verify` makes is made here
# by the same code: `app/api/verification_service.py`. What is new is only the
# part that is genuinely new — a request-scoped, authorized, bounded choice of
# where the evidence comes from, frozen before any work happens and committed
# to the signed result.

router = APIRouter(prefix="/v1/judge", tags=["judge"], dependencies=[Depends(limit_per_key)])


def _capabilities(session: JudgeSession | None) -> dict:
    """Safe metadata only: what exists, what is allowed, what is left.

    Never a Nokia key, never a Gemini key, never an access code, never a base
    URL a caller could steer. `real_available` is a statement about
    configuration, not about connectivity: nothing here contacts Nokia, and
    rendering this must never be mistaken for a successful hosted call.
    """
    allowance = judge_access.snapshot(session)
    return {
        "contract_version": nac_contract.contract_version(),
        "sources": [
            {
                "id": EvidenceSource.MOCK_NOKIA.value,
                "available": True,
                "requires_access": False,
            },
            {
                "id": EvidenceSource.NOKIA_SIMULATOR.value,
                "available": bool(settings.judge_real_nac_enabled and settings.nac_api_key),
                "requires_access": True,
                "unavailable_reason": (
                    None
                    if settings.judge_real_nac_enabled and settings.nac_api_key
                    else "real_source_disabled"
                ),
            },
        ],
        "scenarios": evidence.scenario_catalogue(),
        "planners": [p.value for p in JudgePlanner],
        "gemini_configured": bool(settings.gemini_api_key),
        "operations": sorted(nac_contract.contract()["operations"]),
        "allowance": allowance,
        # Whether /v1/judge/api-keys will issue anything here. A statement about
        # configuration: keys are only minted where the default provider is the
        # mock, so a key from a page can never reach a billable call.
        "api_keys": {
            "available": not makes_billable_calls(settings),
            "requires_access": True,
            "ttl_seconds": settings.judge_api_key_ttl_seconds,
            "provider": settings.provider,
            "planner_default": settings.planner,
        },
        # Configuration readiness, said in the words the runbook uses so a badge
        # can never be read as "a Nokia call succeeded".
        "readiness": (
            "configured_connection_not_verified"
            if settings.judge_real_nac_enabled and settings.nac_api_key
            else "mock_only"
        ),
    }


@router.get("/capabilities")
async def judge_capabilities(
    judge_session: str = Header(default="", alias=SESSION_HEADER),
) -> dict:
    """What this deployment offers. Free of provider and model operations."""
    return _capabilities(judge_access.get(judge_session.strip() or None))


@router.post("/session", dependencies=[Depends(limit_per_ip)])
async def judge_session_start() -> dict:
    """Mint an ordinary judge session: mock evidence, no NaC capability.

    Deliberately unauthenticated and cheap. A judge should be able to run the
    mock demonstration the moment the page loads, and holding this token is
    explicitly not authorization to spend anything.
    """
    record = judge_access.mint()
    return {
        "session": record.token,
        "expires_in_seconds": record.seconds_remaining(time.time()),
        "capabilities": _capabilities(record),
    }


class JudgeAccessRequest(BaseModel):
    model_config = {"extra": "forbid"}

    access_code: str = Field(min_length=1, max_length=128)


@router.post("/access")
async def judge_grant_access(
    body: JudgeAccessRequest,
    session: JudgeSessionDep,
) -> dict:
    """Exchange an organizer-issued code for the bounded NaC capability.

    This exchange is the only way the capability is ever granted. Selecting
    "Real NaC" in the page does not grant it, and does not make a request; a
    public demo token cannot carry it at all. That is what keeps R12's guard —
    public demo tokens never authorize spend — true while the real path exists.
    """
    try:
        record = judge_access.grant_nac(session.token, body.access_code)
    except JudgeAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return {"granted": True, "capabilities": _capabilities(record)}


def _api_key_view(issued: JudgeApiKey, *, reveal: bool) -> dict:
    now = time.time()
    return {
        # The key itself travels exactly once, in the response that minted it.
        # Listing shows a prefix, enough to recognise which key is which.
        "api_key": issued.key if reveal else None,
        "prefix": issued.key[:10] + "…",
        "owner": issued.owner,
        "expires_in_seconds": issued.seconds_remaining(now),
    }


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def judge_mint_api_key(
    body: JudgeAccessRequest,
    session: JudgeSessionDep,
) -> dict:
    """Mint a merchant API key for this judge, behind the organizer's code.

    The code travels in the body of this one request and is checked the same
    way `/access` checks it; it is never stored. The key that comes back works
    on every `Authorization: Bearer` route — `/v1/verify`, the chain reads, the
    receipt verification, Ask-the-agent — as the judge's own tenant, so a
    chain created from a terminal is readable from this same session.

    Refused on a deployment whose default provider makes billable calls: a
    key minted from a page must never authorize those (R12), and the bounded
    judge path is the only route to real Nokia evidence.
    """
    try:
        issued = judge_access.mint_api_key(session.token, body.access_code)
    except JudgeAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return {
        **_api_key_view(issued, reveal=True),
        "provider": settings.provider,
        "planner_default": settings.planner,
        "capabilities": _capabilities(session),
    }


@router.get("/api-keys")
async def judge_list_api_keys(session: JudgeSessionDep) -> dict:
    """This session's live keys, by prefix only. Never the key, never another judge's."""
    return {
        "keys": [_api_key_view(k, reveal=False) for k in judge_access.api_keys_for(session)],
        "capabilities": _capabilities(session),
    }


def _validated_context(
    body: JudgeRunRequest, session: JudgeSession, run_id: str | None
) -> evidence.RunContext:
    """Freeze the choice before anything is spent, or refuse it.

    Everything this returns is fixed for the life of the run: the source, the
    scenario, the contract the mock and the adapter are both checked against,
    the planner, the policy bytes and the owner. The dropdown can change while
    the run is in flight; this cannot.
    """
    if body.scenario not in nac_contract.paired_scenarios():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "unsupported_scenario",
                "message": (
                    "That scenario is not one of the paired Nokia cases. The custom "
                    "mock stories are demonstration fixtures and are not available "
                    "as real Nokia requests."
                ),
            },
        )
    if body.evidence_source is EvidenceSource.NOKIA_SIMULATOR:
        if not settings.judge_real_nac_enabled or not settings.nac_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "real_source_disabled",
                    "message": (
                        "Real Nokia requests are not enabled on this deployment. Mock "
                        "evidence is unaffected and still runs."
                    ),
                },
            )
        if not session.nac_capability:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "nac_capability_required",
                    "message": (
                        "This session is not authorized for real Nokia requests. Enter "
                        "the organizer's access code, or run the mock source."
                    ),
                },
            )
    return evidence.RunContext(
        source=body.evidence_source,
        scenario=body.scenario,
        contract_version=nac_contract.contract_version(),
        planner=body.planner,
        policy_digest=evidence.policy_digest(),
        run_id=run_id or "",
        owner=session.owner,
    )


@router.post("/run")
async def judge_run(
    body: JudgeRunRequest,
    session: JudgeSessionDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    console_run_id: str | None = Header(default=None, alias="X-Console-Run-Id"),
) -> dict:
    """One paired investigation, from a source the judge chose.

    The order of the three things that happen before any spend is the point:
    the choice is validated, the session's capability is checked, and the
    allowance is reserved — all before either Nokia or Gemini is contacted. An
    unauthorized real request therefore fails without costing a model call.
    """
    ctx = _validated_context(body, session, console_run_id)
    request = evidence.request_for(ctx.scenario)
    commitment = subject.request_commitment(
        JudgeRunCommitment(
            request=request,
            evidence_source=ctx.source,
            evidence_environment=ctx.environment,
            scenario=ctx.scenario,
            contract_version=ctx.contract_version,
            planner=ctx.planner,
            policy_digest=ctx.policy_digest,
        )
    )

    real = ctx.source is EvidenceSource.NOKIA_SIMULATOR
    reservation: str | None = None
    if real:
        try:
            reservation = judge_access.reserve_real_run(
                session, settings.judge_nac_attempts_per_run
            )
        except AllowanceExhausted as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": exc.code, "message": exc.message},
            ) from exc
        except JudgeAccessError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": exc.code, "message": exc.message},
            ) from exc

    log: nac_contract.AttemptLog | None = None
    clean = False
    try:
        # Built inside the try, so a failure to construct the adapter still
        # settles: a reservation that is never settled holds this deployment's
        # single real-run slot against every judge who comes after.
        provider, log = evidence.build_provider(ctx)
        engine = build_engine_for_pricing()
        planner = (
            LLMPlanner(engine, max_calls=settings.judge_gemini_calls_per_run)
            if ctx.planner is JudgePlanner.GEMINI
            else GreedyPlanner(engine)
        )

        def stamp(verdict) -> None:
            # Inside the signed bytes, before signing. A source label beside a
            # signature can be edited; one inside it cannot.
            verdict.evidence_source = ctx.evidence_source_label
            verdict.evidence_environment = ctx.environment
            verdict.contract_version = ctx.contract_version
            if log is not None:
                log.seal()
            verdict.outbound_attempts = log.count if log is not None else 0

        result = await verification_service.execute(
            req=request,
            owner=session.owner,
            request_hash=commitment,
            provider=provider,
            idempotency_key=idempotency_key,
            run_id=console_run_id,
            planner=planner,
            available_actions=set(evidence.PAIRED_ACTIONS),
            stamp=stamp,
        )
        clean = True
    except HTTPException:
        # A refusal is not a spend. Every HTTPException `execute` raises comes
        # from the idempotency guard, which answers before an investigator is
        # ever built, so a judge who replays one key across the two modes must
        # not lose a run's whole allowance to a request that never left this
        # process. Read from the attempt log rather than assumed: only a run
        # that provably reserved nothing outbound is released.
        clean = log is None or log.count == 0
        raise
    finally:
        if log is not None:
            log.seal()
        if reservation is not None:
            # A run that did not finish cleanly keeps its whole reservation: a
            # timed-out SDK thread may still be running at the operator, and an
            # attempt whose reservation was released is how a demonstration
            # spends twice for one question. The refusal above is the one
            # exception, and only because it is provable rather than assumed.
            judge_access.settle_real_run(
                session, reservation, log.count if log is not None else 0, clean=clean
            )

    await verification_service.remember(result)
    payload = result.response.model_dump(mode="json")
    payload["judge"] = {
        **ctx.as_metadata(),
        "replayed": result.replayed,
        "outbound_attempts": log.count,
        # The serialized request and the sanitized response shape, so a reader
        # can see what actually went on the wire. Never a header value.
        "attempts": log.as_records(),
        "allowance": judge_access.snapshot(session),
    }
    return payload
