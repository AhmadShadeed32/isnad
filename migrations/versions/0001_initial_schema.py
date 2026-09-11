"""Create the production schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chains",
        sa.Column("chain_id", sa.String(length=40), nullable=False),
        sa.Column("owner_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("hypothesis", sa.String(length=32), nullable=False),
        sa.Column("verdict_json", sa.Text(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("signed_at", sa.String(length=40), nullable=False),
        sa.Column("public_key", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("chain_id"),
    )
    op.create_index("ix_chains_owner_hash", "chains", ["owner_hash"])

    op.create_table(
        "call_announcements",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("institution_id", sa.String(length=64), nullable=False),
        sa.Column("owner_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("calling_participant_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("called_participant_hash", sa.String(length=64), nullable=False),
        sa.Column("strategy", sa.String(length=24), nullable=False, server_default="BRAND_DISPLAY"),
        sa.Column("display_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("call_reason", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_call_announcements_institution_id", "call_announcements", ["institution_id"])
    op.create_index("ix_call_announcements_owner_hash", "call_announcements", ["owner_hash"])
    op.create_index("ix_call_announcements_calling_participant_hash", "call_announcements", ["calling_participant_hash"])
    op.create_index("ix_call_announcements_expires_at", "call_announcements", ["expires_at"])

    op.create_table(
        "screen_events",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("caller_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("callee_hash", sa.String(length=64), nullable=False),
        sa.Column("owner_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_screen_events_caller_hash", "screen_events", ["caller_hash"])
    op.create_index("ix_screen_events_owner_hash", "screen_events", ["owner_hash"])
    op.create_index("ix_screen_events_at", "screen_events", ["at"])
    op.create_index(
        "ix_screen_events_owner_caller_at", "screen_events", ["owner_hash", "caller_hash", "at"]
    )

    op.create_table(
        "announcement_uses",
        sa.Column("announcement_id", sa.String(length=40), nullable=False),
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("announcement_id", "owner_hash"),
    )


def downgrade() -> None:
    op.drop_table("announcement_uses")
    op.drop_index("ix_screen_events_owner_caller_at", table_name="screen_events")
    op.drop_index("ix_screen_events_at", table_name="screen_events")
    op.drop_index("ix_screen_events_owner_hash", table_name="screen_events")
    op.drop_index("ix_screen_events_caller_hash", table_name="screen_events")
    op.drop_table("screen_events")
    op.drop_index("ix_call_announcements_expires_at", table_name="call_announcements")
    op.drop_index("ix_call_announcements_calling_participant_hash", table_name="call_announcements")
    op.drop_index("ix_call_announcements_owner_hash", table_name="call_announcements")
    op.drop_index("ix_call_announcements_institution_id", table_name="call_announcements")
    op.drop_table("call_announcements")
    op.drop_index("ix_chains_owner_hash", table_name="chains")
    op.drop_table("chains")
