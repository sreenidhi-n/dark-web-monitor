"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

role_enum = sa.Enum("admin", "analyst", "readonly", name="role")
channel_enum = sa.Enum("email", "slack", "webhook", name="alertchannel")


def upgrade() -> None:
    role_enum.create(op.get_bind(), checkfirst=True)
    channel_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("admin", "analyst", "readonly", name="role"), nullable=False, server_default="analyst"),
        sa.Column("api_key", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("api_key", name="uq_users_api_key"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_api_key", "users", ["api_key"])

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("onion_url", sa.Text(), nullable=False),
        sa.Column("crawl_frequency_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("onion_url", name="uq_sources_onion_url"),
    )

    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("content_snippet", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("matched_keywords", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("content_hash", name="uq_findings_content_hash"),
    )
    op.create_index("ix_findings_source_id", "findings", ["source_id"])
    op.create_index("ix_findings_content_hash", "findings", ["content_hash"])

    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("domains", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("emails", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_watchlists_owner_id", "watchlists", ["owner_id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("watchlist_id", sa.Integer(), sa.ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_id", sa.Integer(), sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("channel", sa.Enum("email", "slack", "webhook", name="alertchannel"), nullable=False),
        sa.Column("delivered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alerts_watchlist_id", "alerts", ["watchlist_id"])
    op.create_index("ix_alerts_finding_id", "alerts", ["finding_id"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("watchlists")
    op.drop_table("findings")
    op.drop_table("sources")
    op.drop_table("users")
    channel_enum.drop(op.get_bind(), checkfirst=True)
    role_enum.drop(op.get_bind(), checkfirst=True)
