"""S7 — the two unbounded amplifiers: session quota, and the key file mode."""

from __future__ import annotations

import asyncio
import os
import stat
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.chain.vault import InsecureVaultKey, VaultSigner
from app.config import settings
from app.events import current_owner
from app.main import app
from app.ownership import owner_hash
from app.providers.mock import MockProvider
from app.session.manager import SessionManager, SessionQuotaExceeded

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


# --- (a) the session monitor -------------------------------------------------


def test_a_days_ttl_is_rejected():
    """The acceptance criterion: ttl_seconds 86400 -> 422.

    One such request polled SIM Swap and Device Swap every 1.5s for a day:
    115,200 billed CAMARA calls from one unauthenticated-in-effect request.
    """
    response = client.post(
        "/v1/sessions", headers=AUTH, json={"phone_number": "+962790000001", "ttl_seconds": 86400}
    )
    assert response.status_code == 422


def test_a_ttl_at_the_ceiling_is_accepted():
    response = client.post(
        "/v1/sessions",
        headers=AUTH,
        json={"phone_number": "+962790000001", "ttl_seconds": settings.session_max_ttl_seconds},
    )
    assert response.status_code == 200
    client.delete(f"/v1/sessions/{response.json()['session_id']}", headers=AUTH)


@pytest.mark.asyncio
async def test_ttl_is_clamped_even_when_the_edge_is_bypassed():
    mgr = SessionManager()
    rec = await mgr.create(
        "+962790000001", ttl_seconds=86400, poll_seconds=0.05, provider=MockProvider()
    )
    try:
        span = (rec.expires_at - rec.created_at).total_seconds()
        assert span <= settings.session_max_ttl_seconds
    finally:
        await mgr.end(rec.id)


@pytest.mark.asyncio
async def test_concurrent_sessions_per_owner_are_capped():
    mgr = SessionManager()
    token = current_owner.set(owner_hash("a-single-key"))
    created = []
    try:
        for _ in range(settings.session_max_per_owner):
            created.append(
                await mgr.create(
                    "+962790000001", ttl_seconds=30, poll_seconds=5, provider=MockProvider()
                )
            )
        with pytest.raises(SessionQuotaExceeded):
            await mgr.create(
                "+962790000001", ttl_seconds=30, poll_seconds=5, provider=MockProvider()
            )
    finally:
        for rec in created:
            await mgr.end(rec.id)
        current_owner.reset(token)


@pytest.mark.asyncio
async def test_the_cap_is_per_owner_not_global():
    mgr = SessionManager()
    first = current_owner.set(owner_hash("key-one"))
    mine = []
    try:
        for _ in range(settings.session_max_per_owner):
            mine.append(
                await mgr.create(
                    "+962790000001", ttl_seconds=30, poll_seconds=5, provider=MockProvider()
                )
            )
        current_owner.set(owner_hash("key-two"))
        other = await mgr.create(
            "+962790000001", ttl_seconds=30, poll_seconds=5, provider=MockProvider()
        )
        assert other is not None
        await mgr.end(other.id)
    finally:
        current_owner.set(owner_hash("key-one"))
        for rec in mine:
            await mgr.end(rec.id)
        current_owner.reset(first)


@pytest.mark.asyncio
async def test_terminal_records_are_pruned():
    """`_sessions` was never pruned, so it grew for the life of the process.

    Pruning is now on a clock, not on the next `create`: a terminal record is
    deliberately kept for `session_terminal_retention_seconds` so a client
    polling for the expiry it was waiting on can actually read it (R09). What
    this test guards is the original defect — that records accumulate forever —
    so it prunes past that window rather than immediately.
    """
    mgr = SessionManager()
    token = current_owner.set(owner_hash("pruning-key"))
    try:
        rec = await mgr.create(
            "+962790000001", ttl_seconds=30, poll_seconds=5, provider=MockProvider()
        )
        await mgr.end(rec.id)
        await asyncio.sleep(0.01)
        assert rec.id in mgr._sessions, "the terminal status must stay readable for its window"
        rec.terminal_at = rec.terminal_at - timedelta(
            seconds=settings.session_terminal_retention_seconds + 1
        )
        second = await mgr.create(
            "+962790000001", ttl_seconds=30, poll_seconds=5, provider=MockProvider()
        )
        assert rec.id not in mgr._sessions
        await mgr.end(second.id)
    finally:
        current_owner.reset(token)


@pytest.mark.asyncio
async def test_the_poll_floor_applies_only_to_the_billable_path(monkeypatch):
    mgr = SessionManager()
    captured: dict = {}

    async def fake_monitor(rec, poll, provider):
        captured["poll"] = poll

    monkeypatch.setattr(mgr, "_monitor", fake_monitor)

    monkeypatch.setattr(settings, "provider", "nac")
    rec = await mgr.create(
        "+962790000001", ttl_seconds=30, poll_seconds=1.5, provider=MockProvider()
    )
    await asyncio.sleep(0)
    assert captured["poll"] >= settings.session_min_poll_seconds_nac
    await mgr.end(rec.id)

    monkeypatch.setattr(settings, "provider", "hybrid")
    monkeypatch.setattr(settings, "live_evidence_actions", "sim_swap")
    monkeypatch.setattr(settings, "live_evidence_numbers", "+962790000002")
    rec = await mgr.create(
        "+962790000002", ttl_seconds=30, poll_seconds=0.05, provider=MockProvider()
    )
    await asyncio.sleep(0)
    assert captured["poll"] >= settings.session_min_poll_seconds_nac
    await mgr.end(rec.id)

    monkeypatch.setattr(settings, "provider", "mock")
    rec = await mgr.create(
        "+962790000002", ttl_seconds=30, poll_seconds=0.05, provider=MockProvider()
    )
    await asyncio.sleep(0)
    assert captured["poll"] == 0.05  # the stage demo still reacts in a second
    await mgr.end(rec.id)


# --- (b) the vault key file --------------------------------------------------


def test_a_new_key_is_written_owner_only(tmp_path):
    """The acceptance criterion: stat the key -> 600, the directory -> 700.

    It was written with no mode argument, inheriting umask 022 as 0644. Any
    local user or co-tenant process could read it and forge chains that verify —
    the entire tamper-evidence pitch rests on this file.
    """
    key_path = tmp_path / ".isnad" / "vault-key.pem"
    VaultSigner(key_path)

    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(key_path.parent.stat().st_mode) == 0o700


def test_loading_a_world_readable_key_is_refused(tmp_path):
    key_path = tmp_path / "vault-key.pem"
    VaultSigner(key_path)
    os.chmod(key_path, 0o644)

    with pytest.raises(InsecureVaultKey, match="readable beyond its owner"):
        VaultSigner(key_path)


def test_loading_a_group_readable_key_is_refused(tmp_path):
    key_path = tmp_path / "vault-key.pem"
    VaultSigner(key_path)
    os.chmod(key_path, 0o640)

    with pytest.raises(InsecureVaultKey):
        VaultSigner(key_path)


def test_a_passphrase_encrypts_the_key_at_rest(tmp_path, monkeypatch):
    key_path = tmp_path / "vault-key.pem"
    monkeypatch.setattr(settings, "vault_key_passphrase", "a-strong-passphrase")

    signer = VaultSigner(key_path)
    assert b"ENCRYPTED" in key_path.read_bytes()

    # And it round-trips: the same passphrase reopens the same key.
    assert VaultSigner(key_path).public_key_hex() == signer.public_key_hex()
