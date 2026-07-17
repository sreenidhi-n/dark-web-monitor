"""Shared fixtures for the test suite.

Uses an in-memory SQLite database (aiosqlite) so no running PostgreSQL is
required. Each test function gets a fresh schema to prevent state leaking
between tests.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers all models with Base.metadata
from app.database import Base, get_db
from app.main import app
from app.models.user import Role, User
from app.routers.auth import create_access_token, pwd_context

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ── Database fixtures ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def engine():
    """Fresh in-memory SQLite DB per test function."""
    _engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    await _engine.dispose()


@pytest_asyncio.fixture()
async def db(engine):
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session


# ── HTTP client fixture ───────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def client(db):
    """AsyncClient wired to the FastAPI app with the test DB and ES mocked out."""

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db

    mock_es = MagicMock()
    mock_es.close = AsyncMock()

    with (
        patch("app.main.get_es_client", return_value=mock_es),
        patch("app.main.ensure_index", new=AsyncMock()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ── User fixtures ─────────────────────────────────────────────────────────────


async def _make_user(db, email: str, role: Role) -> User:
    user = User(
        email=email,
        password_hash=pwd_context.hash("password"),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture()
async def admin_user(db) -> User:
    return await _make_user(db, "admin@test.com", Role.admin)


@pytest_asyncio.fixture()
async def analyst_user(db) -> User:
    return await _make_user(db, "analyst@test.com", Role.analyst)


@pytest_asyncio.fixture()
async def readonly_user(db) -> User:
    return await _make_user(db, "readonly@test.com", Role.readonly)


# ── Auth header helpers ───────────────────────────────────────────────────────


def bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.email)}"}
