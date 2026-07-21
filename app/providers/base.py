from __future__ import annotations

from typing import Protocol

from app.chain.models import EvidenceLink
from app.domain.enums import Action
from app.domain.schemas import VerificationRequest


class EvidenceProvider(Protocol):
    """Uniform contract for every source of network evidence.

    The agent calls `gather(action, request)` and always receives a normalized
    EvidenceLink — it never sees a raw CAMARA payload, so no coordinate or raw
    phone metadata reaches the reasoning layer or is persisted.
    """

    async def gather(self, action: Action, request: VerificationRequest) -> EvidenceLink: ...
