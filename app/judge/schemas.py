"""Request and commitment models for the judge's paired demonstration.

The commitment model is the load-bearing one. `subject.request_commitment`
hashes whatever Pydantic model it is given, so putting the evidence source,
scenario, contract version and planner *inside* that model is what makes them
part of the run's idempotency identity and of the signed request hash. Without
it, replaying a mock run's key while asking for real evidence would return the
mock result wearing a real label — the exact failure the contender review found
in a peer project's global real-mode flag.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.schemas import VerificationRequest
from app.judge.evidence import EvidenceSource, JudgePlanner


class JudgeRunRequest(BaseModel):
    """What the page sends. Unknown fields are refused, never ignored.

    `model_config` forbids extras on purpose: a JSON field Pydantic silently
    drops is how a request asks for real evidence and quietly gets whatever the
    global provider was configured for.
    """

    model_config = {"extra": "forbid"}

    evidence_source: EvidenceSource
    scenario: str = Field(min_length=1, max_length=64)
    planner: JudgePlanner = JudgePlanner.GREEDY


class JudgeRunCommitment(BaseModel):
    """Everything this run is committed to, in one canonical serialization."""

    model_config = {"extra": "forbid"}

    request: VerificationRequest
    evidence_source: EvidenceSource
    evidence_environment: str
    scenario: str
    contract_version: str
    planner: JudgePlanner
    policy_digest: str
