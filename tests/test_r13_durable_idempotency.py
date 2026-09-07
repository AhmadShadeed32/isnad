"""R13 — the mapping from an idempotency key to its signed chain must be durable.

The window: `/v1/verify` committed the signed chain, then wrote the `done`
entry to `app.cache`. A crash, a cancellation or a failed cache write in
between left a signed chain with no way back to it — and the default memory
cache lost every completed entry on restart anyway. The retry saw no
reservation, investigated again, and paid the operator a second time for a
question that had already been answered and signed.

"Restart" is modelled here as the loss of the cache, because that is exactly
what a restart does to a process-local cache: the durable claim under test is
that the answer is still reachable once the cache that held it is gone. A
genuine second process is not started; the row's survival across one is a
property of the database, and the migration is what provides it.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.api import routes_verify
from app.cache import CacheUnavailable, cache
from app.chain.models import EvidenceLink
from app.db import operations
from app.domain.enums import Action
from app.main import app
from app.ownership import owner_hash
from app.providers.mock import MockProvider

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}
BODY = {"phone_number": "+99999991001", "context": {"event": "signup"}}


class CountingProvider:
    """Wraps the mock and counts what a second investigation would have cost."""

    def __init__(self) -> None:
        self.calls: list[Action] = []
        self._inner = MockProvider()

    async def gather(self, action: Action, request) -> EvidenceLink:
        self.calls.append(action)
        return await self._inner.gather(action, request)

    async def enrich_timing(self, action: Action, request, signal: str):
        return await self._inner.enrich_timing(action, request, signal)


@pytest.fixture
def provider(monkeypatch):
    p = CountingProvider()
    monkeypatch.setattr(routes_verify, "get_live_provider", lambda *a, **k: p)
    return p


@pytest.fixture
def key():
    return f"r13-{uuid.uuid4().hex}"


def _forget_cache() -> None:
    """What a restart does to a process-local cache."""
    getattr(cache, "_store", {}).clear()


def _op(key_value: str):
    return operations.get(owner_hash("demo-merchant-key"), operations.key_digest(key_value))


# --- the acceptance case ---------------------------------------------------


def test_retry_after_a_lost_cache_replays_without_a_second_investigation(provider, key):
    first = client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)
    assert first.status_code == 200
    spent = len(provider.calls)
    assert spent > 0, "the first request did no work, so this proves nothing"

    _forget_cache()
    second = client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)

    assert second.status_code == 200
    assert second.json()["chain_id"] == first.json()["chain_id"]
    assert len(provider.calls) == spent, "the retry re-investigated and re-charged"


def test_a_failed_cache_write_after_the_chain_commits_does_not_lose_the_mapping(
    provider, key, monkeypatch
):
    """The exact crash window: the chain is committed, the cache write fails.

    The cache is an accelerator now, so its failure is logged and the request
    still succeeds — and, crucially, the retry still finds the original answer.
    Before, this window silently lost the mapping and the retry paid again.
    """

    def explode(*args, **kwargs):
        raise CacheUnavailable("cache unavailable")

    monkeypatch.setattr(cache, "set", explode)
    first = client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)
    assert first.status_code == 200
    spent = len(provider.calls)

    monkeypatch.undo()
    _forget_cache()
    retry = client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)

    assert retry.status_code == 200
    assert retry.json()["chain_id"] == first.json()["chain_id"]
    assert len(provider.calls) == spent, "the retry re-investigated and re-charged"
    assert _op(key).state == operations.DONE


def test_a_crash_after_the_chain_commits_still_maps_the_key_to_the_chain(
    provider, key, monkeypatch
):
    """Fail between the commit and the response, the way a crash does."""
    original = routes_verify._response_for
    calls = {"n": 0}

    def crash_once(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("died after committing the chain")
        return original(*args, **kwargs)

    monkeypatch.setattr(routes_verify, "_response_for", crash_once)
    with pytest.raises(RuntimeError):
        client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)
    spent = len(provider.calls)

    # The chain committed and the mapping committed with it, in one transaction.
    assert _op(key).state == operations.DONE

    monkeypatch.undo()
    _forget_cache()
    retry = client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)

    assert retry.status_code == 200
    assert len(provider.calls) == spent, "the retry re-investigated and re-charged"


def test_the_mapping_is_committed_with_the_chain(provider, key):
    response = client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)
    op = _op(key)

    assert op is not None
    assert op.state == operations.DONE
    assert op.chain_id == response.json()["chain_id"]


# --- failures must not silently free a key that may have been spent --------


def test_a_failure_after_work_began_requires_reconciliation(provider, key, monkeypatch):
    """Uncertain work is refused on retry, never repeated."""

    async def fail(*args, **kwargs):
        raise RuntimeError("provider exploded mid-investigation")

    monkeypatch.setattr(provider, "gather", fail)
    with pytest.raises(RuntimeError):
        client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)

    assert _op(key).state == operations.UNCERTAIN

    monkeypatch.undo()
    retry = client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)

    assert retry.status_code == 409
    assert retry.json()["detail"]["code"] == "idempotency_reconciliation_required"
    assert provider.calls == [], "a key that may have been spent was retried"


def test_an_orphaned_pending_row_is_refused_rather_than_repeated(provider, key, monkeypatch):
    """A process that died mid-flight leaves `pending` with nobody working on it."""
    owner = owner_hash("demo-merchant-key")
    key_hash = operations.key_digest(key)
    request_hash = None

    first = client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)
    assert first.status_code == 200
    request_hash = _op(key).request_hash

    # Rewind the row to what a crashed request leaves behind.
    from datetime import UTC, datetime, timedelta

    from app.db.database import SessionLocal
    from app.db.models import VerificationOperationRow

    with SessionLocal() as s:
        row = s.get(VerificationOperationRow, (owner, key_hash))
        row.state = operations.PENDING
        row.chain_id = None
        row.updated_at = datetime.now(UTC) - timedelta(days=1)
        s.commit()
    _forget_cache()
    before = len(provider.calls)

    retry = client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)

    assert retry.status_code == 409
    assert retry.json()["detail"]["code"] == "idempotency_reconciliation_required"
    assert len(provider.calls) == before
    assert request_hash  # the commitment is what a body change is compared against


def test_a_key_reused_with_a_different_body_is_a_conflict(provider, key):
    client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=BODY)
    _forget_cache()
    before = len(provider.calls)

    other = {"phone_number": "+99999991002", "context": {"event": "signup"}}
    response = client.post("/v1/verify", headers={**AUTH, "Idempotency-Key": key}, json=other)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "idempotency_key_reused"
    assert len(provider.calls) == before


def test_a_concurrent_request_on_the_same_key_is_in_progress_not_reconciliation(key):
    """A live in-flight request is distinguished from a crashed one by its lease."""
    owner = owner_hash("demo-merchant-key")
    assert operations.reserve(owner, operations.key_digest(key), "some-hash") is None

    second = operations.reserve(owner, operations.key_digest(key), "some-hash")

    assert second is not None
    assert second.state == operations.PENDING
    assert not second.is_orphaned(), "a fresh reservation must not read as abandoned"


def test_another_owner_cannot_replay_or_block_a_key(key):
    """The reservation is per owner: `Idempotency-Key` values are caller-chosen
    and two merchants picking "order-1" must not collide.

    Asserted at the operations layer rather than through the API, because the
    suite authenticates one merchant key and a second valid key would have to
    be invented for the test rather than described by it.
    """
    key_hash = operations.key_digest(key)
    mine = owner_hash("demo-merchant-key")
    theirs = owner_hash("some-other-merchant-key")

    assert operations.reserve(mine, key_hash, "hash-a") is None
    # The same caller-chosen key, a different owner: free to proceed.
    assert operations.reserve(theirs, key_hash, "hash-b") is None
    # And the same owner reusing it is still blocked.
    assert operations.reserve(mine, key_hash, "hash-a") is not None


# --- retention -------------------------------------------------------------


def test_uncertain_rows_outlive_settled_ones(key, monkeypatch):
    """Deleting an unresolved row turns an answerable question into a re-charge."""
    from datetime import UTC, datetime, timedelta

    from app.db.database import SessionLocal
    from app.db.models import VerificationOperationRow

    owner = owner_hash("demo-merchant-key")
    stale = datetime.now(UTC) - timedelta(days=2)
    with SessionLocal() as s:
        s.add(
            VerificationOperationRow(
                owner_hash=owner, key_hash="a" * 64, request_hash="h",
                state=operations.DONE, chain_id="chn_x", created_at=stale, updated_at=stale,
            )
        )
        s.add(
            VerificationOperationRow(
                owner_hash=owner, key_hash="b" * 64, request_hash="h",
                state=operations.UNCERTAIN, chain_id=None, created_at=stale, updated_at=stale,
            )
        )
        s.commit()

    operations.purge_expired()

    assert operations.get(owner, "a" * 64) is None, "a settled row past its TTL was kept"
    assert operations.get(owner, "b" * 64) is not None, "an unresolved row was deleted"
