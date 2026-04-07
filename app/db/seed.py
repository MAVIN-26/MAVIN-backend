"""
Initial seed data:
- Allergens
- Categories
- Subscription plan
- site_admin account
"""

import asyncio

import bcrypt as _bcrypt
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Allergen, Category, SubscriptionPlan, User
from app.models.user import UserRole

def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()

ALLERGENS = ["Глютен", "Молоко", "Яйца", "Орехи", "Соя", "Рыба", "Моллюски", "Кунжут"]
CATEGORIES = ["Бургеры", "Суши", "Пицца", "Здоровая еда", "Десерты", "Напитки"]

ADMIN_EMAIL = "admin@mavin.ru"
ADMIN_PASSWORD = "admin123"
ADMIN_PHONE = "+70000000000"


async def seed():
    async with AsyncSessionLocal() as session:
        # Allergens
        for name in ALLERGENS:
            exists = await session.scalar(select(Allergen).where(Allergen.name == name))
            if not exists:
                session.add(Allergen(name=name))

        # Categories
        for name in CATEGORIES:
            exists = await session.scalar(select(Category).where(Category.name == name))
            if not exists:
                session.add(Category(name=name))

        # Subscription plan
        plan_exists = await session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.name == "Студент+"))
        if not plan_exists:
            session.add(SubscriptionPlan(name="Студент+", price=199, duration_days=30))

        # site_admin
        admin_exists = await session.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if not admin_exists:
            session.add(User(
                email=ADMIN_EMAIL,
                phone=ADMIN_PHONE,
                password_hash=_hash_password(ADMIN_PASSWORD),
                first_name="Site",
                last_name="Admin",
                role=UserRole.site_admin,
            ))

        await session.commit()
        print("Seed completed.")


if __name__ == "__main__":
    asyncio.run(seed())
