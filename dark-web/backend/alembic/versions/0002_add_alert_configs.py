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
    # Use raw SQL to avoid SQLAlchemy re-creating the alertchannel enum
    # type (which already exists from migration 0001) via op.create_table().
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS alert_configs (
            id            SERIAL PRIMARY KEY,
            watchlist_id  INTEGER NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
            channel       alertchannel NOT NULL,
            destination   VARCHAR(512) NOT NULL,
            is_active     BOOLEAN NOT NULL DEFAULT true,
            created_at    TIMESTAMPTZ DEFAULT now()
        )
    """))
    op.create_index("ix_alert_configs_watchlist_id", "alert_configs", ["watchlist_id"])


def downgrade() -> None:
    op.drop_index("ix_alert_configs_watchlist_id", table_name="alert_configs")
    op.drop_table("alert_configs")
