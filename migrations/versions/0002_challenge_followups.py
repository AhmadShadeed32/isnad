"""Add CHALLENGE followups: challenge_attempts, challenge_events, idempotency_records.

Revision ID: 0002_challenge_followups
Revises: 0001_initial_schema
Create Date: 2026-09-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_challenge_followups"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "challenge_attempts",
        sa.Column("attempt_id", sa.String(length=40), nullable=False),
        sa.Column("chain_id", sa.String(length=40), nullable=False),
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("terminal_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("attempt_id"),
    )
    op.create_index("ix_challenge_attempts_chain_id", "challenge_attempts", ["chain_id"])
    op.create_index("ix_challenge_attempts_owner_hash", "challenge_attempts", ["owner_hash"])
    op.create_index("ix_challenge_attempts_expires_at", "challenge_attempts", ["expires_at"])

    op.create_table(
        "challenge_events",
        sa.Column("event_id", sa.String(length=40), nullable=False),
        sa.Column("attempt_id", sa.String(length=40), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("provenance", sa.String(length=24), nullable=False, server_default="merchant_reported"),
        sa.Column("reported_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_challenge_events_attempt_id", "challenge_events", ["attempt_id"])

    op.create_table(
        "idempotency_records",
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("owner_hash", "operation", "idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
    op.drop_index("ix_challenge_events_attempt_id", table_name="challenge_events")
    op.drop_table("challenge_events")
    op.drop_index("ix_challenge_attempts_expires_at", table_name="challenge_attempts")
    op.drop_index("ix_challenge_attempts_owner_hash", table_name="challenge_attempts")
    op.drop_index("ix_challenge_attempts_chain_id", table_name="challenge_attempts")
    op.drop_table("challenge_attempts")
