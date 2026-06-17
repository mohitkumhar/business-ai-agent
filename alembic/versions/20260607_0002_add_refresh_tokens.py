"""Add refresh_tokens table.

Revision ID: 20260607_0002
Revises: 20260528_0001
Create Date: 2026-06-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260607_0002"
down_revision: Union[str, None] = "20260528_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column("revoked", sa.Boolean(), server_default=sa.text("FALSE"), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.users.user_id"],
            name="refresh_tokens_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="refresh_tokens_pkey"),
        sa.UniqueConstraint("token_hash", name="refresh_tokens_token_hash_key"),
        schema="public",
    )
    op.create_index(
        "idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema="public"
    )
    op.create_index(
        "idx_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], schema="public"
    )


def downgrade() -> None:
    op.drop_index("idx_refresh_tokens_token_hash", table_name="refresh_tokens", schema="public")
    op.drop_index("idx_refresh_tokens_user_id", table_name="refresh_tokens", schema="public")
    op.drop_table("refresh_tokens", schema="public")
