from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.db.database import Base


class UtcDateTime(TypeDecorator):
    """A datetime column that is timezone-aware UTC on both sides.

    SQLite's DATETIME ignores tzinfo: an aware UTC value is written as its naive
    UTC components and READ BACK NAIVE. Everything in this app builds datetimes
    with `datetime.now(timezone.utc)`, so writes and SQL comparisons agreed and
    nothing was wrong — but subtracting a value read back from a row from an
    aware `now` raises TypeError, and that is a trap sitting under every future
    "how long is left on this?".

    Bind: normalize to UTC, then drop the tzinfo the backend would ignore
    anyway, so a value handed in as +03:00 is stored as the same instant rather
    than as its local clock face. Result: re-attach UTC. Rows written before
    this existed read back correctly, because they were already naive UTC.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=UTC)


class ChainRow(Base):
    """A persisted, signed evidence chain. Only chain evidence is stored — never
    raw network signals."""

    __tablename__ = "chains"

    chain_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    # sha256 of the API key that issued this chain. Every read and delete filters
    # on it: without it any key could fetch any other key's chain (S3). Chain ids
    # are 80 bits, so the exposure was horizontal rather than brute-forceable —
    # but with S1's published key the horizon was everyone.
    owner_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    decision: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    hypothesis: Mapped[str] = mapped_column(String(32))
    verdict_json: Mapped[str] = mapped_column(Text)  # exact bytes that were signed
    signature: Mapped[str] = mapped_column(Text)  # Ed25519, hex
    signed_at: Mapped[str] = mapped_column(String(40))
    public_key: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))


class CallAnnouncementRow(Base):
    """A call an institution said it was about to place — CAMARA VerifiedCaller.

    The inversion that makes a PBX call verifiable at all. No CAMARA API can
    attest a SIP trunk, because there is no SIM to ask about; so instead of
    interrogating the call, the institution announces it from an authenticated
    channel, and the callee's check asks whether a matching announcement exists.

    The callee is stored only as an HMAC under the subject pepper (S5). An
    institution announcing a call is telling this service who it is about to
    ring, and a plaintext column would turn that into a customer list.
    """

    __tablename__ = "call_announcements"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    # Which institution the announcing key is bound to. Never taken from the
    # request body: an announcement is only worth anything because the party
    # making it proved who they were, and a self-declared institution id would
    # hand any key holder the right to speak as a bank.
    institution_id: Mapped[str] = mapped_column(String(64), index=True)
    owner_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    # A pre-announcement only needs equality matching later; retaining the raw
    # calling number would create a second phone-number database for no benefit.
    calling_participant_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    called_participant_hash: Mapped[str] = mapped_column(String(64), index=True)
    strategy: Mapped[str] = mapped_column(String(24), default="BRAND_DISPLAY")
    display_name: Mapped[str] = mapped_column(String(120), default="")
    call_reason: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))
    # Absolute expiry rather than a TTL to add at read time: a row that has
    # outlived its window must be unusable even if the reader forgets to check,
    # and the spec's advice is a window measured in seconds.
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    # An announcement described ONE call. Left uncapped it verified every call
    # presenting that number for the length of its window, so a replayed or
    # leaked announcement was a free pass for a burst rather than for the single
    # call it was made about. Defaults so init_db's additive migration can add
    # both columns to an existing database.
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)


class ScreenEventRow(Base):
    """One Tier 1 screen, kept so velocity can be seen across subscribers.

    Every other check in this system judges a call in isolation. A scam campaign
    is not one call: it is one number reaching hundreds of people in minutes,
    and that shape is invisible to any single-call check no matter how good it
    is. This table is the only place that pattern can be seen — and it is the
    one signal here that gets stronger the more people use the system.

    The callee is an HMAC under the subject pepper, never a number. Counting
    DISTINCT callees needs to tell two people apart; it does not need to know
    who either of them is.
    """

    __tablename__ = "screen_events"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    # The velocity query needs a stable equality key, not the raw caller E.164.
    caller_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    callee_hash: Mapped[str] = mapped_column(String(64))
    # Which tenant observed this call. WITHOUT IT THE SIGNAL IS POISONABLE:
    # counting across every tenant let any key holder send ~30 screens with
    # invented callees and mark any bank's switchboard as a spoof for everybody
    # for the length of the window, and nothing recorded who did it.
    owner_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    at: Mapped[datetime] = mapped_column(UtcDateTime, index=True, default=lambda: datetime.now(UTC))

    # The velocity query filters on owner AND caller AND a time window. Separate
    # single-column indexes make SQLite pick one and scan the rest.
    __table_args__ = (Index("ix_screen_events_owner_caller_at", "owner_hash", "caller_hash", "at"),)


class AnnouncementUseRow(Base):
    """One subscriber's single use of one announcement.

    A global counter was worse than no counter. `find(consume=True)` spent the
    only use for whoever screened FIRST, and screening is open to any key
    holder — so an attacker could spray screens at (bank, victim) and burn every
    announcement the bank made, guaranteeing the victim's genuine calls always
    read UNKNOWN. The cap handed a third party a kill switch for the mechanism.

    Scoping the use to the reader fixes both directions: an attacker can only
    spend their own, and a reader who never screened a call cannot later mint an
    evidence chain from someone else's announcement.
    """

    __tablename__ = "announcement_uses"

    announcement_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    owner_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))
