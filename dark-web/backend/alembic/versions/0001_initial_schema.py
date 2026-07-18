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


def upgrade() -> None:
    # Create enum types first via raw DDL with duplicate-safe DO blocks.
    # Using raw SQL here intentionally to avoid SQLAlchemy re-attempting
    # CREATE TYPE inside op.create_table when it copies Enum column types.
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE role AS ENUM ('admin', 'analyst', 'readonly'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    ))
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE alertchannel AS ENUM ('email', 'slack', 'webhook'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    ))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS users (
            id          SERIAL PRIMARY KEY,
            email       VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role        role NOT NULL DEFAULT 'analyst',
            api_key     VARCHAR(64),
            is_active   BOOLEAN NOT NULL DEFAULT true,
            created_at  TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_users_email    UNIQUE (email),
            CONSTRAINT uq_users_api_key  UNIQUE (api_key)
        )
    """))
    op.create_index("ix_users_email",   "users", ["email"])
    op.create_index("ix_users_api_key", "users", ["api_key"])

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS sources (
            id                     SERIAL PRIMARY KEY,
            name                   VARCHAR(255) NOT NULL,
            onion_url              TEXT NOT NULL,
            crawl_frequency_hours  INTEGER NOT NULL DEFAULT 24,
            last_crawled_at        TIMESTAMPTZ,
            is_active              BOOLEAN NOT NULL DEFAULT true,
            created_at             TIMESTAMPTZ DEFAULT now(),
            created_by_id          INTEGER REFERENCES users(id) ON DELETE SET NULL,
            CONSTRAINT uq_sources_onion_url UNIQUE (onion_url)
        )
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS findings (
            id               SERIAL PRIMARY KEY,
            source_id        INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            url              TEXT NOT NULL,
            title            VARCHAR(512),
            content_snippet  TEXT NOT NULL,
            content_hash     VARCHAR(64) NOT NULL,
            matched_keywords JSON NOT NULL DEFAULT '[]',
            first_seen       TIMESTAMPTZ DEFAULT now(),
            last_seen        TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_findings_content_hash UNIQUE (content_hash)
        )
    """))
    op.create_index("ix_findings_source_id",    "findings", ["source_id"])
    op.create_index("ix_findings_content_hash", "findings", ["content_hash"])

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS watchlists (
            id         SERIAL PRIMARY KEY,
            name       VARCHAR(255) NOT NULL,
            owner_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            keywords   JSON NOT NULL DEFAULT '[]',
            domains    JSON NOT NULL DEFAULT '[]',
            emails     JSON NOT NULL DEFAULT '[]',
            is_active  BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    op.create_index("ix_watchlists_owner_id", "watchlists", ["owner_id"])

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS alerts (
            id              SERIAL PRIMARY KEY,
            watchlist_id    INTEGER NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
            finding_id      INTEGER NOT NULL REFERENCES findings(id)   ON DELETE CASCADE,
            triggered_at    TIMESTAMPTZ DEFAULT now(),
            channel         alertchannel NOT NULL,
            delivered       BOOLEAN NOT NULL DEFAULT false,
            acknowledged    BOOLEAN NOT NULL DEFAULT false,
            acknowledged_at TIMESTAMPTZ
        )
    """))
    op.create_index("ix_alerts_watchlist_id", "alerts", ["watchlist_id"])
    op.create_index("ix_alerts_finding_id",   "alerts", ["finding_id"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("watchlists")
    op.drop_table("findings")
    op.drop_table("sources")
    op.drop_table("users")
    op.execute(sa.text("DROP TYPE IF EXISTS alertchannel"))
    op.execute(sa.text("DROP TYPE IF EXISTS role"))
