from __future__ import annotations

from typing import Protocol

from app.chain.models import EvidenceLink, EvidenceTiming
from app.domain.enums import Action
from app.domain.schemas import VerificationRequest


class EvidenceProvider(Protocol):
    """Uniform contract for every source of network evidence.

    The agent calls `gather(action, request)` and always receives a normalized
    EvidenceLink — it never sees a raw CAMARA payload, so no coordinate or raw
    phone metadata reaches the reasoning layer or is persisted.
    """

    async def gather(self, action: Action, request: VerificationRequest) -> EvidenceLink: ...

    async def enrich_timing(
        self, action: Action, request: VerificationRequest, signal: str
    ) -> EvidenceTiming:
        """Optional: when the operator says the change in `signal` happened.

        A SEPARATE priced operation, not a field of `gather`'s answer, and the
        investigator charges it separately. A provider without one is not
        broken — `app.providers.timing.unsupported` is the honest reply, and
        the investigator treats a provider that does not implement this method
        at all the same way.

        Implementations must never raise: a date that did not arrive has to
        leave the boolean evidence exactly as it was.
        """
        from app.providers import timing

        return timing.unsupported(action)
