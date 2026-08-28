"""Add billing and saved searches tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-04
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create subscriptions table
    op.create_table(
        "subscriptions",
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tier", sa.Text(), server_default="free", nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True),
        sa.Column("stripe_subscription_id", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 2. Create saved_searches table
    op.create_table(
        "saved_searches",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("alert_interval", sa.Text(), server_default="weekly", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_saved_searches_user_id", "saved_searches", ["user_id"])

def downgrade() -> None:
    op.drop_index("idx_saved_searches_user_id", "saved_searches")
    op.drop_table("saved_searches")
    op.drop_table("subscriptions")
