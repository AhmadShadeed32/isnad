"""Durable idempotency for /v1/verify (R13).

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


def downgrade() -> None:
    op.drop_index("ix_verification_operations_state", table_name="verification_operations")
    op.drop_table("verification_operations")
