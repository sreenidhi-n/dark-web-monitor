"""Bootstrap script — creates the first admin user.

Usage (inside the backend container):
    python scripts/create_admin.py admin@example.com changeme123

Or via make:
    make create-admin email=admin@example.com password=changeme123
"""
import asyncio
import sys

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.user import Role, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin(email: str, password: str) -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print(f"User already exists: {email}")
            await engine.dispose()
            return

        user = User(
            email=email,
            password_hash=pwd_context.hash(password),
            role=Role.admin,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"Admin created: {email}")

    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/create_admin.py <email> <password>")
        sys.exit(1)
    asyncio.run(create_admin(sys.argv[1], sys.argv[2]))
