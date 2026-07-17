"""add alert_configs table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "watchlist_id",
            sa.Integer(),
            sa.ForeignKey("watchlists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.Enum("email", "slack", "webhook", name="alertchannel"),
            nullable=False,
        ),
        sa.Column("destination", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alert_configs_watchlist_id", "alert_configs", ["watchlist_id"])


def downgrade() -> None:
    op.drop_index("ix_alert_configs_watchlist_id", table_name="alert_configs")
    op.drop_table("alert_configs")
