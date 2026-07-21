from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ChainRow(Base):
    """A persisted, signed evidence chain. Only chain evidence is stored — never
    raw network signals."""

    __tablename__ = "chains"

    chain_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    decision: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    hypothesis: Mapped[str] = mapped_column(String(32))
    verdict_json: Mapped[str] = mapped_column(Text)      # exact bytes that were signed
    signature: Mapped[str] = mapped_column(Text)         # Ed25519, hex
    signed_at: Mapped[str] = mapped_column(String(40))
    public_key: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
