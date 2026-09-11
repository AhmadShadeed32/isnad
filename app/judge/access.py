"""Scoped judge sessions and every allowance a real Nokia call must pass.

A judge is not a merchant. They arrive at `/judge` with no credential, must be
able to run the mock demonstration immediately, and must be able to reach the
real Nokia simulator only after an organizer-issued code has been exchanged for
a capability the server holds. Three separate things follow from that:

* **Identity.** Each browser gets its own session, and its own owner. Two judges
  running at the same time must not share evidence, quota, cached decisions,
  receipts or journals, so the session token is the ownership boundary rather
  than a shared "console" tenant.
* **Capability.** The NaC capability is granted by exchanging a code, never by
  holding a page token. This is what preserves R12's guard — a public demo token
  cannot authorize spend — while still making the real path reachable.
* **Allowance.** Per run, per session and per deployment, reserved atomically
  before either external service is called. A failed attempt keeps its
  reservation, because the operator may already have received it.
* **Merchant keys.** A judge who has the code can also mint a short-lived
  `Authorization: Bearer` key and call `/v1/verify` the way a merchant would.
  Only ever issued where the default provider is the mock, so the key can
  reach nothing billable; the bounded judge path stays the only way to Nokia.

Process-local, like `app/model_budget.py` and `app/session/manager.py`: one
worker, one replica, which is the constraint the rest of this service already
documents rather than a new one introduced here.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass, field

from app.config import settings

_MAX_LIVE_SESSIONS = 256
_MAX_LIVE_API_KEYS = 64
SESSION_HEADER = "x-judge-session"
TOKEN_PREFIX = "judge_"
# A merchant key minted for a judge. Distinguishable from a configured key and
# from a console demo token by prefix alone, so a log line or a bug report says
# which kind of credential was presented without revealing any of it.
API_KEY_PREFIX = "mk_"


class JudgeAccessError(RuntimeError):
    """A judge session or capability problem the caller must be told about."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class AllowanceExhausted(JudgeAccessError):
    """A bounded allowance refused this run before anything was spent."""


@dataclass
class JudgeSession:
    token: str
    owner: str
    created_at: float
    expires_at: float
    # False until an organizer code is exchanged. Selecting "Real NaC" in the
    # UI does not set this and does not make any request; only the exchange does.
    nac_capability: bool = False
    nac_attempts_used: int = 0
    runs: int = 0
    granted_at: float | None = None
    reserved: int = 0
    notes: list[str] = field(default_factory=list)

    def is_expired(self, now: float) -> bool:
        return now >= self.expires_at

    def seconds_remaining(self, now: float) -> int:
        return max(0, int(self.expires_at - now))


@dataclass
class JudgeApiKey:
    """A merchant credential a judge minted for themselves behind the access code.

    It carries the judge session's OWNER, not a reference to the session: the
    key must keep working after the 30-minute session that minted it has gone,
    because a judge copies it into a terminal and comes back. What the owner
    buys them is that every chain they create with `curl` lands in the same
    tenant as the page that minted the key, so the page can read it back.
    """

    key: str
    owner: str
    created_at: float
    expires_at: float

    def is_expired(self, now: float) -> bool:
        return now >= self.expires_at

    def seconds_remaining(self, now: float) -> int:
        return max(0, int(self.expires_at - now))


class JudgeAccess:
    """The session store, the code exchange, the key mint and the allowance ledger."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, JudgeSession] = {}
        self._api_keys: dict[str, JudgeApiKey] = {}
        # Each reserved/charged slot belongs to a run. Refunding one run must
        # never remove a concurrent run's newer entries from the rolling hour.
        self._hourly: deque[tuple[str, float]] = deque()
        self._reservations: dict[str, tuple[JudgeSession, int]] = {}
        self._active_real_runs = 0

    # --- sessions ---------------------------------------------------------

    def _sweep(self, now: float) -> None:
        for token, rec in list(self._sessions.items()):
            if rec.is_expired(now):
                del self._sessions[token]

    def mint(self) -> JudgeSession:
        """Issue an ordinary judge session: mock evidence, no NaC capability."""
        now = time.time()
        with self._lock:
            self._sweep(now)
            while len(self._sessions) >= _MAX_LIVE_SESSIONS:
                # Bound the store; a reload loop must not grow memory.
                oldest = min(self._sessions, key=lambda t: self._sessions[t].expires_at)
                del self._sessions[oldest]
            token = TOKEN_PREFIX + secrets.token_urlsafe(32)
            record = JudgeSession(
                token=token,
                owner=owner_for_token(token),
                created_at=now,
                expires_at=now + settings.judge_session_ttl_seconds,
            )
            self._sessions[token] = record
            return record

    def get(self, token: str | None) -> JudgeSession | None:
        if not token:
            return None
        now = time.time()
        with self._lock:
            self._sweep(now)
            record = self._sessions.get(token)
            if record is None or record.is_expired(now):
                return None
            return record

    def require(self, token: str | None) -> JudgeSession:
        record = self.get(token)
        if record is None:
            raise JudgeAccessError(
                "judge_session_required",
                "This judge session is missing or has expired. Start a new one to continue.",
            )
        return record

    # --- capability -------------------------------------------------------

    def grant_nac(self, token: str | None, access_code: str) -> JudgeSession:
        """Exchange an organizer code for the bounded NaC capability.

        The code is never stored on the session and never returned to the
        browser: what the browser gets back is the capability and its
        remaining allowance.
        """
        record = self.require(token)
        if not settings.judge_real_nac_enabled:
            raise JudgeAccessError(
                "real_source_disabled",
                "Real NaC runs are not enabled on this deployment. Mock evidence "
                "remains available and is unaffected.",
            )
        self._require_code(access_code)
        with self._lock:
            record.nac_capability = True
            record.granted_at = time.time()
        return record

    @staticmethod
    def _require_code(access_code: str) -> None:
        """Refuse unless `access_code` is one of the organizer's codes.

        Constant-time compared against every configured code, so a wrong code
        cannot be narrowed by timing. With no codes configured nothing matches,
        which is the safe answer: a capability nobody can name is granted to
        no one, never to everyone.
        """
        codes = settings.judge_codes
        supplied = (access_code or "").strip()
        if not supplied or not any(
            hmac.compare_digest(supplied.encode("utf-8"), code.encode("utf-8")) for code in codes
        ):
            raise JudgeAccessError(
                "invalid_access_code",
                "That access code was not recognized. Ask the organizer for the "
                "current code; mock evidence needs no code at all.",
            )

    # --- merchant keys ----------------------------------------------------

    def _sweep_api_keys(self, now: float) -> None:
        for key, rec in list(self._api_keys.items()):
            if rec.is_expired(now):
                del self._api_keys[key]

    def mint_api_key(self, token: str | None, access_code: str) -> JudgeApiKey:
        """Issue a merchant API key to a judge, behind the organizer's code.

        This is the one way a credential that works on `/v1/verify` is ever
        issued from a page, and it is refused outright on a deployment whose
        default provider reaches the network. That keeps R12's guard by
        construction: the access code authorizes the bounded judge path, and a
        key minted here can only ever drive the mock provider. Where a judge
        needs real Nokia evidence, the judge page's allowance is the route.
        """
        from app.config import makes_billable_calls

        record = self.require(token)
        if makes_billable_calls(settings):
            raise JudgeAccessError(
                "api_keys_disabled",
                "Judge API keys are not issued on this deployment: its default "
                "provider makes billable calls, and a key minted from a page must "
                "never authorize those. Use a configured merchant key instead.",
            )
        self._require_code(access_code)
        now = time.time()
        with self._lock:
            self._sweep_api_keys(now)
            while len(self._api_keys) >= _MAX_LIVE_API_KEYS:
                # Bound the store; a generate-button loop must not grow memory.
                oldest = min(self._api_keys, key=lambda k: self._api_keys[k].expires_at)
                del self._api_keys[oldest]
            key = API_KEY_PREFIX + secrets.token_urlsafe(32)
            issued = JudgeApiKey(
                key=key,
                owner=record.owner,
                created_at=now,
                expires_at=now + settings.judge_api_key_ttl_seconds,
            )
            self._api_keys[key] = issued
            return issued

    def api_key_owner(self, candidate: str) -> str | None:
        """The owner a judge-minted key belongs to, or None if it is not one.

        Looked up rather than iterated: the value is a 256-bit random string,
        so there is no low-entropy prefix for a timing probe to walk.
        """
        if not candidate:
            return None
        now = time.time()
        with self._lock:
            self._sweep_api_keys(now)
            issued = self._api_keys.get(candidate)
            if issued is None or issued.is_expired(now):
                return None
            return issued.owner

    def api_keys_for(self, session: JudgeSession) -> list[JudgeApiKey]:
        """This session's live keys, oldest first, for the page. Never another's."""
        now = time.time()
        with self._lock:
            self._sweep_api_keys(now)
            return sorted(
                (k for k in self._api_keys.values() if k.owner == session.owner),
                key=lambda k: k.created_at,
            )

    # --- allowance --------------------------------------------------------

    def _prune_hour(self, now: float) -> None:
        cutoff = now - 3600.0
        self._hourly = deque(
            (run, at) for run, at in self._hourly
            if at > cutoff or run in self._reservations
        )

    def reserve_real_run(self, session: JudgeSession, attempts: int) -> str:
        """Reserve this run's whole outbound attempt budget, atomically.

        Reserved up front rather than counted as calls happen: two concurrent
        runs must not both pass a check that each of them then invalidates. The
        unused remainder is released only by a run that finished cleanly —
        `settle_real_run` — because a run that timed out may still have work in
        flight at the operator.
        """
        if not session.nac_capability:
            raise JudgeAccessError(
                "nac_capability_required",
                "This session is not authorized for real Nokia requests. Enter the "
                "organizer's access code, or run the mock source instead.",
            )
        now = time.time()
        with self._lock:
            if session.is_expired(now) or self._sessions.get(session.token) is not session:
                raise JudgeAccessError("judge_session_required", "This judge session has expired.")
            self._prune_hour(now)
            if self._active_real_runs >= settings.judge_max_concurrent_real_runs:
                raise AllowanceExhausted(
                    "real_runs_busy",
                    "Another real Nokia run is in progress. Wait for it to finish, "
                    "or run the mock source now.",
                )
            session_left = settings.judge_nac_attempts_per_session - (
                session.nac_attempts_used + session.reserved
            )
            if session_left < attempts:
                raise AllowanceExhausted(
                    "judge_allowance_exhausted",
                    "This judge session has used its Nokia allowance. Previous "
                    "results are unaffected; you can still run the mock source.",
                )
            if len(self._hourly) + attempts > settings.judge_nac_attempts_per_hour:
                raise AllowanceExhausted(
                    "deployment_allowance_exhausted",
                    "This deployment has reached its hourly Nokia allowance. "
                    "Previous results are unaffected; mock evidence still runs.",
                )
            session.reserved += attempts
            self._active_real_runs += 1
            reservation = secrets.token_urlsafe(24)
            self._reservations[reservation] = (session, attempts)
            for _ in range(attempts):
                self._hourly.append((reservation, now))
            return reservation

    def settle_real_run(
        self, session: JudgeSession, reservation: str, attempts_made: int, *, clean: bool
    ) -> None:
        """Reconcile a finished run's reservation with what it actually spent.

        `clean=False` keeps the entire reservation. A timed-out SDK thread may
        still be running, and an abandoned attempt whose reservation was
        released is exactly how a demonstration double-spends.
        """
        now = time.time()
        with self._lock:
            allocation = self._reservations.get(reservation)
            if allocation is None:
                return  # Settlement is idempotent; it cannot refund twice.
            if allocation[0] is not session:
                raise ValueError("reservation belongs to another judge session")
            del self._reservations[reservation]
            self._active_real_runs = max(0, self._active_real_runs - 1)
            reserved = allocation[1]
            session.reserved -= reserved
            spent = reserved if not clean else min(reserved, max(0, attempts_made))
            session.nac_attempts_used += spent
            session.runs += 1
            # Replace only this run's reservation. Charge from settlement time
            # conservatively, so a slow run cannot age out before its calls.
            self._hourly = deque(
                entry for entry in self._hourly if entry[0] != reservation
            )
            self._hourly.extend((reservation, now) for _ in range(spent))
            self._prune_hour(now)

    def snapshot(self, session: JudgeSession | None) -> dict:
        """Safe capability metadata for the page. Never a key, never a code."""
        now = time.time()
        with self._lock:
            self._prune_hour(now)
            deployment_left = max(
                0, settings.judge_nac_attempts_per_hour - len(self._hourly)
            )
            active = self._active_real_runs
        if session is None:
            return {
                "session": False,
                "nac_capability": False,
                "attempts_per_run": settings.judge_nac_attempts_per_run,
                "session_attempts_left": 0,
                "deployment_attempts_left": deployment_left,
                "active_real_runs": active,
                "expires_in_seconds": 0,
            }
        return {
            "session": True,
            "nac_capability": session.nac_capability,
            "attempts_per_run": settings.judge_nac_attempts_per_run,
            "session_attempts_left": max(
                0,
                settings.judge_nac_attempts_per_session
                - session.nac_attempts_used
                - session.reserved,
            ),
            "deployment_attempts_left": deployment_left,
            "active_real_runs": active,
            "expires_in_seconds": session.seconds_remaining(now),
        }

    def clear(self) -> None:
        """For tests, which must not inherit another test's sessions or spend."""
        with self._lock:
            self._sessions.clear()
            self._api_keys.clear()
            self._hourly.clear()
            self._reservations.clear()
            self._active_real_runs = 0


def owner_for_token(token: str) -> str:
    """The tenant a judge session token belongs to.

    A digest, not the token: the owner is written into database rows and into
    the signed verdict's `owner_hash`, and a bearer credential must not be
    recoverable from either.
    """
    return "judge:" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]


access = JudgeAccess()
