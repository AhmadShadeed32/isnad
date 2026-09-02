from __future__ import annotations

import asyncio
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.chain.subject import subject_hash
from app.config import settings
from app.db.database import SessionLocal
from app.db.models import AnnouncementUseRow, CallAnnouncementRow
from app.events import current_owner
from app.ownership import ANONYMOUS, owner_hash

# CAMARA VerifiedCaller strategies. BRAND_DISPLAY shows the registered name on
# the incoming call; SMS asks the network to send the callee a short message
# confirming the call is genuine.
STRATEGY_BRAND_DISPLAY = "BRAND_DISPLAY"
STRATEGY_SMS = "SMS"
STRATEGIES = {STRATEGY_BRAND_DISPLAY, STRATEGY_SMS}


def institution_for_key(api_key: str) -> str | None:
    """Which institution this key may speak for, or None.

    Fails closed and is unset by default, like `merchant_api_keys`. Without this
    binding the whole mechanism inverts into an attack: anyone holding any key
    could announce a call "from" a bank's number and have their own spoofed call
    come back verified. The institution is never read from the request body.
    """
    raw = (settings.institution_keys or "").strip()
    if not raw:
        return None
    # compare_digest, not ==. This decides whether a caller may speak for a
    # bank, and a plain string compare leaks the length of the shared prefix
    # through timing — the one comparison in this file worth walking a key out
    # of. Every configured pair is compared, with no early exit on a match.
    found: str | None = None
    for pair in raw.split(","):
        key, _, institution = pair.partition(":")
        key, institution = key.strip(), institution.strip()
        if key and institution and secrets.compare_digest(key, api_key):
            found = institution
    return found


def _ttl_seconds(requested: int | None) -> int:
    """The window an announcement stays usable.

    Bounded because the window IS the spoofing opportunity: for as long as an
    announcement stands, a call presenting that number verifies. The spec's own
    examples use 45 seconds and advise expiring on call setup.
    """
    ceiling = settings.announce_max_ttl_seconds
    if requested is None:
        return min(settings.announce_ttl_seconds, ceiling)
    return max(1, min(int(requested), ceiling))


def record(
    institution_id: str,
    api_key: str,
    calling_participant: str,
    called_participant: str,
    strategy: str = STRATEGY_BRAND_DISPLAY,
    display_name: str = "",
    call_reason: str = "",
    time_to_live: int | None = None,
) -> tuple[str, datetime]:
    """Store one pre-announcement. Returns (id, expires_at)."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=_ttl_seconds(time_to_live))
    announcement_id = "ann_" + uuid.uuid4().hex[:20]
    with SessionLocal() as session:
        session.add(
            CallAnnouncementRow(
                id=announcement_id,
                institution_id=institution_id,
                owner_hash=owner_hash(api_key),
                calling_participant_hash=subject_hash(calling_participant),
                called_participant_hash=subject_hash(called_participant),
                strategy=strategy,
                display_name=display_name[:120],
                call_reason=call_reason[:160],
                created_at=now,
                expires_at=expires_at,
            )
        )
        session.commit()
    return announcement_id, expires_at


def _owner() -> str:
    """The tenant this request belongs to, set at the auth boundary (S2)."""
    return current_owner.get() or ANONYMOUS


def find(
    calling_participant: str,
    called_participant: str,
    consume: bool = False,
) -> CallAnnouncementRow | None:
    """A live announcement matching this call, or None. Scoped to the reader.

    Matches on BOTH ends. Matching the caller alone would let one genuine
    announcement to one customer verify a burst of spoofed calls to everyone
    else for as long as its window stood.

    USES ARE PER READER, and a global counter was worse than none at all. With
    one shared use, whoever screened FIRST spent it — and screening is open to
    any key holder, so an attacker could spray screens at (bank, victim) and
    burn every announcement the bank made, guaranteeing the victim's genuine
    calls always read UNKNOWN. The cap handed a third party a kill switch for
    the whole mechanism.

    Per reader, both directions close:
      * `consume=True` succeeds once per tenant. An attacker spends only their
        own use and cannot touch the callee's.
      * `consume=False` returns it only to a reader that already holds the use.
        It is an inspection, not a verification, and it mints nothing.

    Both tiers consume. One announcement is worth ONE verification, to one
    party, once — a client uses Tier 1 or Tier 2 for a given call, and whichever
    runs first is the one that gets the credit. A non-spending read on the
    evidence path let a party replay somebody else's announcement into unlimited
    signed, publicly fetchable TRUST_CALLER receipts for a bank's number.
    """
    now = datetime.now(UTC)
    called_hash = subject_hash(called_participant)
    owner = _owner()
    with SessionLocal() as session:
        row = (
            session.query(CallAnnouncementRow)
            .filter(
                CallAnnouncementRow.calling_participant_hash == subject_hash(calling_participant),
                CallAnnouncementRow.called_participant_hash == called_hash,
                CallAnnouncementRow.expires_at > now,
            )
            .order_by(CallAnnouncementRow.expires_at.desc())
            .first()
        )
        if row is None:
            return None

        already = session.get(AnnouncementUseRow, (row.id, owner)) is not None
        if consume:
            if already:
                return None
            session.add(
                AnnouncementUseRow(
                    announcement_id=row.id,
                    owner_hash=owner,
                    at=now,
                )
            )
            try:
                session.commit()
            except IntegrityError:
                # Two concurrent screens for the same reader. The primary key
                # decides; the loser is a re-use, not a first use.
                session.rollback()
                return None
        elif not already:
            return None
        session.expunge_all()
        return row


def purge_expired() -> int:
    """Drop announcements past their window, and the use rows that belonged to
    them. Expiry is already enforced on read; this only stops the tables growing
    without bound.

    The use rows go first and by id: `announcement_uses` has no foreign key, so
    deleting the announcements alone would leave a row per reader per expired
    announcement behind forever — the same unbounded growth, in the table added
    to fix the burn attack.
    """
    now = datetime.now(UTC)
    with SessionLocal() as session:
        # A subquery, not a list of ids read into Python: a sweep that has to
        # bind one parameter per expired row is one SQLite variable limit away
        # from failing exactly when there is most to delete.
        expired = select(CallAnnouncementRow.id).where(CallAnnouncementRow.expires_at <= now)
        session.query(AnnouncementUseRow).filter(
            AnnouncementUseRow.announcement_id.in_(expired)
        ).delete(synchronize_session=False)
        deleted = (
            session.query(CallAnnouncementRow)
            .filter(CallAnnouncementRow.expires_at <= now)
            .delete(synchronize_session=False)
        )
        session.commit()
    return deleted


# SQLite writes block the event loop, and every one of these runs inside an
# async handler — same reasoning as store.py.
async def record_async(*args, **kwargs) -> tuple[str, datetime]:
    return await asyncio.to_thread(record, *args, **kwargs)


async def find_async(*args, **kwargs) -> CallAnnouncementRow | None:
    return await asyncio.to_thread(find, *args, **kwargs)
