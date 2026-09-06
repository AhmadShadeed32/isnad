"""Add run_events (I14).

Revision ID: 0005_run_events
Revises: 0004_proof_shares
Create Date: 2026-09-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_run_events"
down_revision = "0004_proof_shares"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_events",
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("body_json", sa.Text(), nullable=False),
        sa.Column("server_time", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("owner_hash", "run_id", "sequence"),
    )
    op.create_index("ix_run_events_server_time", "run_events", ["server_time"])


def downgrade() -> None:
    op.drop_index("ix_run_events_server_time", table_name="run_events")
    op.drop_table("run_events")
