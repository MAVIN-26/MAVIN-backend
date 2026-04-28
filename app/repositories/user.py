from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole
from app.repositories.base import BaseRepository, PaginatedResult


class UserRepository(BaseRepository[User]):
    model = User

    async def get_with_allergens(self, user_id: int) -> User | None:
        result = await self.db.execute(
            select(User).options(selectinload(User.allergens)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> User | None:
        return await self.db.scalar(select(User).where(User.email == email))

    async def find_by_phone(self, phone: str) -> User | None:
        return await self.db.scalar(select(User).where(User.phone == phone))

    async def find_by_email_excluding(self, email: str, exclude_user_id: int) -> User | None:
        return await self.db.scalar(
            select(User).where(User.email == email, User.id != exclude_user_id)
        )

    async def list_paginated(
        self,
        search: str | None,
        role: UserRole | None,
        page: int,
        limit: int,
    ) -> PaginatedResult[User]:
        base = select(User)
        if role is not None:
            base = base.where(User.role == role)
        if search:
            pattern = f"%{search}%"
            base = base.where(
                or_(
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.phone.ilike(pattern),
                )
            )

        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))

        result = await self.db.execute(
            base.options(selectinload(User.allergens))
            .order_by(User.id.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        items = result.scalars().all()
        return PaginatedResult(items=items, total=total or 0, page=page, limit=limit)
