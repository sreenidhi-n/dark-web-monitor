"""add category to watchlists and severity to findings

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("""
        ALTER TABLE watchlists
            ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'general'
    """))
    op.execute(sa.text("""
        ALTER TABLE findings
            ADD COLUMN IF NOT EXISTS severity VARCHAR(20) NOT NULL DEFAULT 'medium'
    """))
    op.create_index("ix_findings_severity", "findings", ["severity"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_findings_severity", table_name="findings")
    op.execute(sa.text("ALTER TABLE findings DROP COLUMN IF EXISTS severity"))
    op.execute(sa.text("ALTER TABLE watchlists DROP COLUMN IF EXISTS category"))
