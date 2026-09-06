"""Offline fake Number Verification provider (P4a, ISNAD_PROVIDER=nac_fake).

Talks to demo/fake_operator instead of Nokia, over the same manual OIDC flow
NacProvider's non-SDK path uses (app/providers/oidc_flow.py + app/oidc.py) —
so an "offline contract" pass here is exercising the real validation code, not
a parallel stand-in that could silently drift from it. Never a network call
outside localhost; makes_billable_calls() in app/config.py never returns True
for this provider.

Only Number Verification is implemented. Every other action returns
EVIDENCE_UNAVAILABLE: the fake operator has no SIM Swap, Device Swap, Location,
Reachability or Roaming API, and pretending otherwise would misrepresent what
this offline pass actually proves. A merchant journey exercised against this
provider necessarily lands on an UNRESOLVED chain for every other check the
planner chooses to make.
"""

from __future__ import annotations

import httpx

from app.chain.models import EvidenceLink
from app.config import settings
from app.domain.enums import API_LABEL, Action, Result
from app.domain.schemas import VerificationRequest
from app.oidc import IdTokenError
from app.providers import oidc_flow
from app.providers.vocabulary import detail_for

# Fixed, not configurable: this client only ever talks to the local fake
# operator, which is seeded with the same constant. Making it configurable
# would add surface area to a fixture that must never reach a real network.
FAKE_CLIENT_ID = "isnad-fake-merchant"
FAKE_CLIENT_SECRET = "isnad-fake-merchant-secret"


class FakeNacProvider:
    def __init__(self, number_verification_token: str | None = None) -> None:
        self.number_verification_token = number_verification_token
        self._base_url = settings.nac_fake_base_url.rstrip("/")

    async def gather(self, action: Action, request: VerificationRequest) -> EvidenceLink:
        if action == Action.NUMBER_VERIFY:
            return await self._verify_number(request)
        return EvidenceLink(
            step=0,
            action=action,
            api=API_LABEL[action],
            result=Result.INFO,
            signal="EVIDENCE_UNAVAILABLE",
            detail="the offline fake operator implements Number Verification only",
            consent_basis="NaC application authorization",
            source="nac_fake",
            latency_ms=1,
        )

    async def _verify_number(self, request: VerificationRequest) -> EvidenceLink:
        if not self.number_verification_token:
            return EvidenceLink(
                step=0,
                action=Action.NUMBER_VERIFY,
                api=API_LABEL[Action.NUMBER_VERIFY],
                result=Result.INFO,
                signal="CONSENT_REQUIRED",
                detail=detail_for("CONSENT_REQUIRED"),
                consent_basis="NaC authorization / end-user consent",
                source="nac_fake",
                requires_consent=True,
                latency_ms=1,
            )
        async with httpx.AsyncClient(timeout=settings.nac_timeout_seconds) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/verify",
                    headers={"Authorization": f"Bearer {self.number_verification_token}"},
                    json={"phoneNumber": request.phone_number},
                )
                response.raise_for_status()
                body = response.json()
            except httpx.HTTPError as exc:
                return self._failure("PROVIDER_UNAVAILABLE", f"fake operator request failed: {exc}")
        verified = body.get("devicePhoneNumberVerified")
        if verified is True:
            return EvidenceLink(
                step=0,
                action=Action.NUMBER_VERIFY,
                api=API_LABEL[Action.NUMBER_VERIFY],
                result=Result.PASS,
                signal="NUMBER_MATCH",
                detail=detail_for("NUMBER_MATCH"),
                consent_basis="NaC authorization / end-user consent",
                source="nac_fake",
                latency_ms=1,
            )
        if verified is False:
            return EvidenceLink(
                step=0,
                action=Action.NUMBER_VERIFY,
                api=API_LABEL[Action.NUMBER_VERIFY],
                result=Result.FLAG,
                signal="NUMBER_MISMATCH",
                detail=detail_for("NUMBER_MISMATCH"),
                consent_basis="NaC authorization / end-user consent",
                source="nac_fake",
                latency_ms=1,
            )
        return self._failure("EVIDENCE_UNAVAILABLE", "fake operator returned no usable result")

    def _failure(self, signal: str, detail: str) -> EvidenceLink:
        return EvidenceLink(
            step=0,
            action=Action.NUMBER_VERIFY,
            api=API_LABEL[Action.NUMBER_VERIFY],
            result=Result.INFO,
            signal=signal,
            detail=detail,
            consent_basis="NaC authorization / end-user consent",
            source="nac_fake",
            latency_ms=1,
        )

    async def begin_number_verification(
        self, phone_number: str, redirect_uri: str, state: str, nonce: str
    ) -> str:
        return oidc_flow.build_authorization_url(
            authorization_endpoint=f"{self._base_url}/authorize",
            client_id=FAKE_CLIENT_ID,
            redirect_uri=redirect_uri,
            scope=settings.nac_number_verification_scope,
            state=state,
            nonce=nonce,
            login_hint=phone_number,
            # The fake operator is plain HTTP on loopback by design (no local
            # CA to trust). Never relax this for NacProvider's real path.
            require_https=False,
        )

    async def exchange_number_verification_code(
        self, code: str, redirect_uri: str, nonce: str
    ) -> str:
        async with httpx.AsyncClient(timeout=settings.nac_timeout_seconds) as client:
            try:
                return await oidc_flow.complete_number_verification_exchange(
                    http_client=client,
                    token_endpoint=f"{self._base_url}/token",
                    client_id=FAKE_CLIENT_ID,
                    client_secret=FAKE_CLIENT_SECRET,
                    code=code,
                    redirect_uri=redirect_uri,
                    issuer=self._base_url,
                    audience=FAKE_CLIENT_ID,
                    nonce=nonce,
                    jwks_uri=f"{self._base_url}/jwks.json",
                    leeway_seconds=settings.nac_id_token_leeway_seconds,
                )
            except (oidc_flow.OidcFlowError, IdTokenError) as exc:
                raise RuntimeError(str(exc)) from exc
