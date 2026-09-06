"""Add network condition subscriptions and events (gate 6).

Revision ID: 0006_network_conditions
Revises: 0005_run_events
Create Date: 2026-09-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_network_conditions"
down_revision = "0005_run_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "network_condition_subscriptions",
        sa.Column("subscription_id", sa.String(length=40), nullable=False),
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=True),
        sa.Column("device_hash", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("callback_token_digest", sa.String(length=64), nullable=False),
        sa.Column("last_error", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("subscription_id"),
    )
    op.create_index(
        "ix_network_condition_subscriptions_owner_hash",
        "network_condition_subscriptions",
        ["owner_hash"],
    )
    op.create_index(
        "ix_network_condition_subscriptions_provider_id",
        "network_condition_subscriptions",
        ["provider_id"],
    )
    op.create_index(
        "ix_network_condition_subscriptions_device_hash",
        "network_condition_subscriptions",
        ["device_hash"],
    )
    op.create_index(
        "ix_network_condition_subscriptions_status",
        "network_condition_subscriptions",
        ["status"],
    )
    op.create_index(
        "ix_network_condition_subscriptions_expires_at",
        "network_condition_subscriptions",
        ["expires_at"],
    )
    op.create_table(
        "network_condition_events",
        sa.Column("subscription_id", sa.String(length=40), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("subscription_id", "event_id"),
    )
    op.create_index(
        "ix_network_condition_events_occurred_at",
        "network_condition_events",
        ["occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_network_condition_events_occurred_at", table_name="network_condition_events")
    op.drop_table("network_condition_events")
    for name in (
        "expires_at",
        "status",
        "device_hash",
        "provider_id",
        "owner_hash",
    ):
        op.drop_index(
            f"ix_network_condition_subscriptions_{name}",
            table_name="network_condition_subscriptions",
        )
    op.drop_table("network_condition_subscriptions")
