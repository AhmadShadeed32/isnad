"""P4a — consent-contract defects fixed before building the live-consent journey.

Each test below was run against the pre-fix code first and observed failing for
the stated reason.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.chain.subject import request_commitment
from app.consent import ConsentStore
from app.domain.schemas import RequestContext, VerificationRequest, VerificationResponse


def _request(**context_kwargs) -> VerificationRequest:
    return VerificationRequest(
        phone_number="+99999991000",
        context=RequestContext(event="signup", **context_kwargs),
    )


def test_a_completed_consent_survives_a_new_creation_within_retention():
    """_sweep() used to delete a terminal record the instant any create() ran.

    Pre-fix: creating consent B swept A the moment A was COMPLETED, regardless
    of A's own retention window, so a merchant polling A's result mid-poll saw
    a 404 for a run that had genuinely just finished.
    """
    store = ConsentStore(max_records=50, max_records_per_owner=50)
    record_a = store.create(_request(), "key-a", "https://example.test/cb", ttl_seconds=300)
    store.complete(
        record_a,
        response=VerificationResponse(
            decision="ALLOW",
            confidence=0.1,
            hypothesis="h",
            reason="r",
            chain_id="chn_test",
        ),
    )

    # Creating a second, unrelated consent used to sweep every terminal record.
    store.create(_request(), "key-b", "https://example.test/cb", ttl_seconds=300)

    assert record_a.consent_id in store._records
    assert store.owned(record_a.consent_id, "key-a") is not None


def test_a_terminal_record_is_swept_after_its_retention_window():
    """Retention is bounded, not indefinite: it must eventually go away."""
    store = ConsentStore(max_records=50, max_records_per_owner=50, terminal_retention_seconds=0)
    record_a = store.create(_request(), "key-a", "https://example.test/cb", ttl_seconds=300)
    store.deny(record_a)

    store.create(_request(), "key-b", "https://example.test/cb", ttl_seconds=300)

    assert record_a.consent_id not in store._records


def test_create_generates_a_nonce_independent_of_state():
    """Before P4a, `state` was the only random value; nonce did not exist."""
    store = ConsentStore()
    record = store.create(_request(), "key-a", "https://example.test/cb", ttl_seconds=300)

    assert record.nonce
    assert record.nonce != record.state
    another = store.create(_request(), "key-b", "https://example.test/cb", ttl_seconds=300)
    assert another.nonce != record.nonce


def test_the_request_and_its_commitment_are_frozen_at_creation():
    """A mutable request object must not change the subject/context after approval.

    Pre-fix: `request_hash` was recomputed from `record.request` at completion
    time in routes_consent.py, and `record.request` was the same object handed
    in at create() — so mutating it after approval silently changed what the
    eventual receipt commits to.
    """
    store = ConsentStore()
    original_request = _request(account_age_days=1)
    record = store.create(original_request, "key-a", "https://example.test/cb", ttl_seconds=300)
    expected_hash = request_commitment(original_request)
    assert record.request_hash == expected_hash

    # Mutate the caller's object (and, before the fix, the record's own
    # reference to the same object) after the consent was created.
    original_request.context.account_age_days = 999

    assert record.request.context.account_age_days == 1, "create() must snapshot, not alias"
    assert record.request_hash == expected_hash, "the commitment must not track a later mutation"


def test_deny_clears_the_access_token():
    """Every terminal transition must clear the token; deny() did not.

    deny() only ever fires from PENDING/EXCHANGING today, where a token is not
    normally set yet — but the contract is "every terminal transition clears
    it", not "clears it when one happens to be present". Set one directly
    (defense-in-depth: nothing should assume the caller never will) and check
    deny() still clears it.
    """
    store = ConsentStore()
    record = store.create(_request(), "key-a", "https://example.test/cb", ttl_seconds=300)
    store.begin_callback(record)  # PENDING -> EXCHANGING
    record.access_token = "sensitive-token"

    store.deny(record)

    assert record.access_token is None


def test_expiring_a_stale_record_also_stamps_a_terminal_time():
    """A record that times out without ever being touched must still get a
    terminal_at, or it would never leave the store once past its TTL."""
    store = ConsentStore(terminal_retention_seconds=0)
    record = store.create(_request(), "key-a", "https://example.test/cb", ttl_seconds=0)
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)

    store.create(_request(), "key-b", "https://example.test/cb", ttl_seconds=300)

    assert record.consent_id not in store._records
