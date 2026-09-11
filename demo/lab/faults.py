"""I4 — a lab-only fault-injecting provider wrapper.

Wraps a real provider (the mock fixture provider in every actual use) and
substitutes a normalized, allowlisted evidence result for the requested
action instead of calling through. This never touches NaC and never
monkeypatches a shared provider instance another session might be using —
each caller constructs its own wrapper around its own provider.

`Investigator._call()` does not catch a raw provider exception, so this
deliberately never raises: raising `TimeoutError` here would abort the
investigation before a verdict, not demonstrate the intended unresolved
result. Every profile maps to the same normalized signal a real provider
failure already produces.
"""

from __future__ import annotations

from app.chain.models import EvidenceLink
from app.domain.enums import API_LABEL, Action, Result
from app.domain.schemas import VerificationRequest
from app.providers.vocabulary import detail_for

ALLOWED_PROFILES = frozenset({"none", "timeout", "unavailable", "consent_required", "delayed"})

_PROFILE_SIGNAL = {
    "timeout": "PROVIDER_UNAVAILABLE",
    "unavailable": "EVIDENCE_UNAVAILABLE",
    "consent_required": "CONSENT_REQUIRED",
}


class UnknownFaultProfile(ValueError):
    pass


class FaultInjectingProvider:
    def __init__(self, inner, profile: str = "none", delay_seconds: float = 0.05) -> None:
        if profile not in ALLOWED_PROFILES:
            raise UnknownFaultProfile(profile)
        self._inner = inner
        self._profile = profile
        self._delay_seconds = delay_seconds

    async def gather(self, action: Action, request: VerificationRequest) -> EvidenceLink:
        if self._profile == "none":
            return await self._inner.gather(action, request)
        if self._profile == "delayed":
            import asyncio

            # A bounded, in-process delay for a demo/test clock, never a real
            # network wait — the delay itself is the "recovery took time" beat.
            await asyncio.sleep(self._delay_seconds)
            return await self._inner.gather(action, request)

        signal = _PROFILE_SIGNAL[self._profile]
        return EvidenceLink(
            step=0,  # overwritten by Investigator._call()
            action=action,
            api=API_LABEL[action],
            result=Result.INFO,
            signal=signal,
            detail=detail_for(signal),
            source="lab_fault",
            requires_consent=signal == "CONSENT_REQUIRED",
        )
