"""
Create a site_admin user.

Reads credentials from environment variables:
    SITE_ADMIN_EMAIL
    SITE_ADMIN_PASSWORD
    SITE_ADMIN_PHONE

Usage:
    python -m app.cli.create_site_admin
"""

import asyncio
import os
import sys

import bcrypt
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import User
from app.models.user import UserRole


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Error: environment variable {name} is not set", file=sys.stderr)
        sys.exit(1)
    return value


async def create_site_admin() -> None:
    email = _require_env("SITE_ADMIN_EMAIL")
    password = _require_env("SITE_ADMIN_PASSWORD")
    phone = _require_env("SITE_ADMIN_PHONE")

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is not None:
            print(f"User with email {email} already exists (id={existing.id})")
            return

        session.add(
            User(
                email=email,
                phone=phone,
                password_hash=_hash_password(password),
                first_name="Site",
                last_name="Admin",
                role=UserRole.site_admin,
            )
        )
        await session.commit()
        print(f"Created site_admin: {email}")


if __name__ == "__main__":
    asyncio.run(create_site_admin())
