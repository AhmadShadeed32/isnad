from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.chain.models import EvidenceLink
from app.domain.enums import Decision


class Money(BaseModel):
    value: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class Area(BaseModel):
    """A claimed location — never a tracked coordinate. Used only for yes/no verify."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_m: int = Field(default=2000, gt=0, le=50000)


class RequestContext(BaseModel):
    event: Literal["signup", "checkout", "payout", "password_reset", "profile_change", "inbound_call", "session_monitor"] = "checkout"
    amount: Optional[Money] = None
    payment_method: Optional[str] = None  # e.g. "cod", "card"
    account_age_days: Optional[int] = Field(default=None, ge=0)
    claimed_location: Optional[Area] = None


class VerifyOptions(BaseModel):
    return_chain: bool = True


class VerificationRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+[1-9]\d{7,14}$", examples=["+962790000001"])
    context: RequestContext = Field(default_factory=RequestContext)
    options: VerifyOptions = Field(default_factory=VerifyOptions)


class VerificationResponse(BaseModel):
    decision: Decision
    confidence: float
    hypothesis: str
    reason: str
    chain_id: str
    chain: Optional[List[EvidenceLink]] = None
    evidence_cost: float = 0.0
    latency_ms: int = 0
    evidence_steps: int = 0
    provider_sources: List[str] = Field(default_factory=list)


ConsentStatus = Literal[
    "PENDING",
    "EXCHANGING",
    "AUTHORIZED",
    "VERIFYING",
    "COMPLETED",
    "DENIED",
    "FAILED",
    "EXPIRED",
]


class NumberVerificationConsentResponse(BaseModel):
    consent_id: str
    status: ConsentStatus
    authorization_url: Optional[str] = None
    expires_at: str
    chain_id: Optional[str] = None
    reason: Optional[str] = None


# --- Reverse Isnad: verify an inbound caller to the customer ---

class ReverseVerificationRequest(BaseModel):
    caller_number: str = Field(..., pattern=r"^\+[1-9]\d{7,14}$", examples=["+96265000000"])
    claimed_identity: str = Field(..., min_length=2, max_length=120, examples=["Bank of Jordan"])
    customer_number: Optional[str] = Field(
        default=None, pattern=r"^\+[1-9]\d{7,14}$"
    )
    options: VerifyOptions = Field(default_factory=VerifyOptions)


class ReverseVerificationResponse(BaseModel):
    trust: str                     # TRUST_CALLER | CAUTION | REJECT_CALLER
    confidence: float              # P(impersonation)
    claimed_identity: str
    reason: str
    chain_id: str
    chain: Optional[List[EvidenceLink]] = None


# --- Trust with a TTL: live session revocation ---

class SessionCreateRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+[1-9]\d{7,14}$", examples=["+962790000001"])
    ttl_seconds: Optional[int] = Field(default=None, ge=0, le=86400)


class SessionResponse(BaseModel):
    session_id: str
    status: str                    # ACTIVE | REVOKED | ENDED | EXPIRED
    phone_number: str
    reason: Optional[str] = None
    created_at: str
    expires_at: str
