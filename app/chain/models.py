from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field

from app.domain.enums import Action, Decision, Result


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _chain_id() -> str:
    return "chn_" + uuid.uuid4().hex[:20]


class EvidenceLink(BaseModel):
    """One attested link in the chain — the normalized result of one CAMARA call.

    Note: we deliberately store the *verdict-relevant* fact only (PASS/FLAG + a
    human sentence), never the raw signal (no coordinate or raw phone metadata).
    """

    step: int
    action: Action
    api: str                       # human-readable CAMARA API label
    result: Result
    signal: str                    # normalized signal name, e.g. "SIM_SWAPPED"
    detail: str                    # plain-language, e.g. "swap detected 41 min ago"
    consent_basis: str = "n/a"
    source: str = "unknown"        # mock, nac, or another normalized provider
    requires_consent: bool = False
    latency_ms: int = 0
    delta_logodds: float = 0.0     # how much this link moved the belief
    at: datetime = Field(default_factory=_now)


class Verdict(BaseModel):
    decision: Decision
    confidence: float              # P(fraud) at decision time, 0..1
    hypothesis: str
    reason: str
    chain_id: str
    chain: List[EvidenceLink] = Field(default_factory=list)
    evidence_cost: float = 0.0
    latency_ms: int = 0
    provider_sources: List[str] = Field(default_factory=list)


class Chain(BaseModel):
    id: str = Field(default_factory=_chain_id)
    hypothesis: str = ""
    links: List[EvidenceLink] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    signed: Optional[str] = None   # Ed25519 signature over the chain (see chain/vault.py)

    def add(self, link: EvidenceLink) -> None:
        self.links.append(link)

    def next_step(self) -> int:
        return len(self.links) + 1
