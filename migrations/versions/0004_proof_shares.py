"""Add proof_shares (I13).

Revision ID: 0004_proof_shares
Revises: 0003_outcomes
Create Date: 2026-09-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_proof_shares"
down_revision = "0003_outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proof_shares",
        sa.Column("share_id", sa.String(length=40), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("chain_id", sa.String(length=40), nullable=False),
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="summary"),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("share_id"),
    )
    op.create_index("ix_proof_shares_token_digest", "proof_shares", ["token_digest"], unique=True)
    op.create_index("ix_proof_shares_chain_id", "proof_shares", ["chain_id"])
    op.create_index("ix_proof_shares_owner_hash", "proof_shares", ["owner_hash"])
    op.create_index("ix_proof_shares_expires_at", "proof_shares", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_proof_shares_expires_at", table_name="proof_shares")
    op.drop_index("ix_proof_shares_owner_hash", table_name="proof_shares")
    op.drop_index("ix_proof_shares_chain_id", table_name="proof_shares")
    op.drop_index("ix_proof_shares_token_digest", table_name="proof_shares")
    op.drop_table("proof_shares")
