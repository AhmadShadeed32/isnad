"""Durable idempotency for /v1/verify (R13), and the network-condition live index (R07).

Revision ID: 0007_verification_operations
Revises: 0006_network_conditions
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_verification_operations"
down_revision = "0006_network_conditions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "verification_operations",
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("chain_id", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("owner_hash", "key_hash"),
    )
    op.create_index(
        "ix_verification_operations_state", "verification_operations", ["state"]
    )
    # R07: the subscription quota check filters on exactly these three columns.
    op.create_index(
        "ix_network_condition_subscriptions_live",
        "network_condition_subscriptions",
        ["owner_hash", "status", "expires_at"],
    )
    # Pre-existing drift, found by the new schema-parity test: this index is
    # declared on the model, so every `create_all` database has had it and no
    # migrated database ever did. Repaired here rather than in a migration of
    # its own, because it has no separate history worth recording.
    op.create_index(
        "ix_call_announcements_called_participant_hash",
        "call_announcements",
        ["called_participant_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_call_announcements_called_participant_hash", table_name="call_announcements"
    )
    op.drop_index(
        "ix_network_condition_subscriptions_live",
        table_name="network_condition_subscriptions",
    )
    op.drop_index("ix_verification_operations_state", table_name="verification_operations")
    op.drop_table("verification_operations")
