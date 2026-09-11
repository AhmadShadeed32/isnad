"""R07 — settled network-condition rows must be reclaimed, and bounded.

Nothing ever deleted a subscription row. Events were capped per subscription,
which bounds one subscription's events and nothing else: a repeated
create/delete cycle grew the subscription table without limit and carried a
bounded set of events with each row. Expiry changed the reported status and
reclaimed nothing, and the quota check on the create path read every row an
owner had ever created.

What must survive a sweep matters as much as what goes: an `unknown` row is
the only record that a subscription may still be running at the operator.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, inspect

from app import network_conditions, retention
from app.config import settings
from app.db.database import SessionLocal
from app.db.models import Base, NetworkConditionEventRow, NetworkConditionSubscriptionRow


def _subscription(session, subscription_id: str, status: str, expires_at: datetime,
                  owner: str = "owner-a", device: str = "device-a") -> None:
    session.add(
        NetworkConditionSubscriptionRow(
            subscription_id=subscription_id,
            owner_hash=owner,
            device_hash=device,
            provider_kind="mock",
            provider_id=None,
            status=status,
            created_at=expires_at - timedelta(hours=1),
            expires_at=expires_at,
            deleted_at=None,
            last_query_at=None,
            callback_token_digest="d" * 64,
            last_error="",
        )
    )


def _event(session, subscription_id: str, event_id: str) -> None:
    now = datetime.now(UTC)
    session.add(
        NetworkConditionEventRow(
            subscription_id=subscription_id,
            event_id=event_id,
            level="Low",
            occurred_at=now,
            received_at=now,
        )
    )


@pytest.fixture(autouse=True)
def clean_tables():
    with SessionLocal() as s:
        s.query(NetworkConditionEventRow).delete()
        s.query(NetworkConditionSubscriptionRow).delete()
        s.commit()
    yield


def test_a_settled_subscription_and_its_events_are_reclaimed():
    stale = datetime.now(UTC) - timedelta(seconds=settings.network_condition_retention_seconds + 60)
    with SessionLocal() as s:
        _subscription(s, "sub-old", "deleted", stale)
        _event(s, "sub-old", "e1")
        _event(s, "sub-old", "e2")
        s.commit()

    assert network_conditions.purge_terminal() == 1

    with SessionLocal() as s:
        assert s.get(NetworkConditionSubscriptionRow, "sub-old") is None
        assert s.query(NetworkConditionEventRow).count() == 0, "child events were orphaned"


def test_a_recently_settled_subscription_is_kept_for_its_window():
    """A client polling on its own interval must still see the terminal status."""
    recent = datetime.now(UTC) - timedelta(seconds=60)
    with SessionLocal() as s:
        _subscription(s, "sub-recent", "expired", recent)
        s.commit()

    assert network_conditions.purge_terminal() == 0

    with SessionLocal() as s:
        assert s.get(NetworkConditionSubscriptionRow, "sub-recent") is not None


def test_an_active_subscription_is_never_swept():
    future = datetime.now(UTC) + timedelta(hours=1)
    with SessionLocal() as s:
        _subscription(s, "sub-live", "active", future)
        s.commit()

    assert network_conditions.purge_terminal() == 0

    with SessionLocal() as s:
        assert s.get(NetworkConditionSubscriptionRow, "sub-live") is not None


def test_an_unreconciled_subscription_is_never_swept():
    """`unknown` may still be running at the operator; deleting it hides that."""
    stale = datetime.now(UTC) - timedelta(days=30)
    with SessionLocal() as s:
        _subscription(s, "sub-unknown", "unknown", stale)
        s.commit()

    network_conditions.expire_due()
    assert network_conditions.purge_terminal() == 0

    with SessionLocal() as s:
        row = s.get(NetworkConditionSubscriptionRow, "sub-unknown")
        assert row is not None
        assert row.status == "unknown", "an unreconciled row was settled by the sweep"


def test_expiry_is_written_down_so_retention_can_see_it():
    """The clock alone never changed the stored status, so nothing became eligible."""
    stale = datetime.now(UTC) - timedelta(seconds=settings.network_condition_retention_seconds + 60)
    with SessionLocal() as s:
        _subscription(s, "sub-stale", "active", stale)
        s.commit()

    assert network_conditions.expire_due() == 1
    assert network_conditions.purge_terminal() == 1

    with SessionLocal() as s:
        assert s.get(NetworkConditionSubscriptionRow, "sub-stale") is None


def test_a_sweep_is_bounded_however_many_rows_have_accumulated(monkeypatch):
    monkeypatch.setattr(settings, "purge_batch_size", 5)
    stale = datetime.now(UTC) - timedelta(days=7)
    with SessionLocal() as s:
        for i in range(12):
            _subscription(s, f"sub-{i}", "deleted", stale)
        s.commit()

    assert network_conditions.purge_terminal() == 5
    assert network_conditions.purge_terminal() == 5
    assert network_conditions.purge_terminal() == 2
    assert network_conditions.purge_terminal() == 0


def test_the_active_count_ignores_terminal_and_expired_rows():
    """The quota must not be consumed by rows that are no longer live."""
    now = datetime.now(UTC)
    with SessionLocal() as s:
        _subscription(s, "live-1", "active", now + timedelta(hours=1))
        _subscription(s, "gone-1", "deleted", now + timedelta(hours=1))
        _subscription(s, "past-1", "active", now - timedelta(hours=1))
        _subscription(s, "other-owner", "active", now + timedelta(hours=1), owner="owner-b")
        _subscription(s, "other-device", "active", now + timedelta(hours=1), device="device-b")
        s.commit()

        per_owner, per_device = network_conditions._active_counts(s, "owner-a", "device-a", now)

    assert per_owner == 2, "terminal or expired rows were counted as live"
    assert per_device == 1


def test_the_retention_sweep_runs_them():
    stale = datetime.now(UTC) - timedelta(days=7)
    with SessionLocal() as s:
        _subscription(s, "sub-sweep", "deleted", stale)
        s.commit()

    deleted = retention.purge_once()

    assert deleted["network_condition_subscriptions"] == 1
    assert "expired_network_conditions" in deleted


# --- schema parity ----------------------------------------------------------


def test_the_migrations_produce_the_same_schema_as_create_all(tmp_path):
    """The two paths must agree.

    SQLite demos take `create_all`; anything else takes Alembic. Nothing
    compared them, so an index or column added to one and not the other was
    invisible until a non-SQLite deployment behaved differently.
    """
    db = tmp_path / "migrated.db"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=".",
        env={
            "PATH": "/usr/bin:/bin",
            "ISNAD_DATABASE_URL": f"sqlite:///{db}",
            "ISNAD_PROVIDER": "mock",
            "ISNAD_PLANNER": "greedy",
            "ISNAD_GEMINI_API_KEY": "",
            "ISNAD_MERCHANT_API_KEYS": "demo-merchant-key",
        },
        capture_output=True,
        text=True,
        check=False,  # the assertion below reports the failure with its stderr
    )
    assert result.returncode == 0, f"alembic upgrade head failed:\n{result.stderr}"

    fresh = tmp_path / "created.db"
    engine = create_engine(f"sqlite:///{fresh}")
    Base.metadata.create_all(engine)

    migrated = inspect(create_engine(f"sqlite:///{db}"))
    created = inspect(engine)

    migrated_tables = set(migrated.get_table_names()) - {"alembic_version"}
    assert migrated_tables == set(created.get_table_names())

    for table in sorted(migrated_tables):
        assert {c["name"] for c in migrated.get_columns(table)} == {
            c["name"] for c in created.get_columns(table)
        }, f"columns differ on {table}"
        assert {i["name"] for i in migrated.get_indexes(table)} == {
            i["name"] for i in created.get_indexes(table)
        }, f"indexes differ on {table}"
