"""Add merchant_outcome_events (P5).

Revision ID: 0003_outcomes
Revises: 0002_challenge_followups
Create Date: 2026-09-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_outcomes"
down_revision = "0002_challenge_followups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merchant_outcome_events",
        sa.Column("event_id", sa.String(length=40), nullable=False),
        sa.Column("chain_id", sa.String(length=40), nullable=False),
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("dimension", sa.String(length=24), nullable=False),
        sa.Column("value", sa.String(length=24), nullable=False),
        sa.Column("basis", sa.String(length=32), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("reported_at", sa.DateTime(), nullable=False),
        sa.Column("late_report", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supersedes_event_id", sa.String(length=40), nullable=True),
        sa.Column("superseded_by", sa.String(length=40), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_merchant_outcome_events_chain_id", "merchant_outcome_events", ["chain_id"])
    op.create_index("ix_merchant_outcome_events_owner_hash", "merchant_outcome_events", ["owner_hash"])
    op.create_index("ix_merchant_outcome_events_superseded_by", "merchant_outcome_events", ["superseded_by"])
    op.create_index(
        "ux_outcome_current_per_dimension",
        "merchant_outcome_events",
        ["owner_hash", "chain_id", "dimension"],
        unique=True,
        sqlite_where=sa.text("superseded_by IS NULL"),
        postgresql_where=sa.text("superseded_by IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_outcome_current_per_dimension", table_name="merchant_outcome_events")
    op.drop_index("ix_merchant_outcome_events_superseded_by", table_name="merchant_outcome_events")
    op.drop_index("ix_merchant_outcome_events_owner_hash", table_name="merchant_outcome_events")
    op.drop_index("ix_merchant_outcome_events_chain_id", table_name="merchant_outcome_events")
    op.drop_table("merchant_outcome_events")
