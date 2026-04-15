from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.restaurant import Restaurant
from app.repositories.base import BaseRepository, PaginatedResult


class RestaurantRepository(BaseRepository[Restaurant]):
    model = Restaurant

    async def list_active_paginated(
        self,
        category_id: int | None,
        search: str | None,
        page: int,
        limit: int,
    ) -> PaginatedResult[Restaurant]:
        base = select(Restaurant).where(Restaurant.is_active.is_(True))
        if category_id is not None:
            base = base.join(Restaurant.categories).where(Category.id == category_id)
        if search:
            base = base.where(Restaurant.name.ilike(f"%{search}%"))

        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))
        result = await self.db.execute(
            base.options(selectinload(Restaurant.categories))
            .order_by(Restaurant.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        items = result.unique().scalars().all()
        return PaginatedResult(items=items, total=total or 0, page=page, limit=limit)

    async def list_all_paginated(self, page: int, limit: int) -> PaginatedResult[Restaurant]:
        total = await self.db.scalar(select(func.count(Restaurant.id)))
        result = await self.db.execute(
            select(Restaurant)
            .options(selectinload(Restaurant.categories))
            .order_by(Restaurant.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        items = result.scalars().all()
        return PaginatedResult(items=items, total=total or 0, page=page, limit=limit)

    async def get_active_with_categories(self, restaurant_id: int) -> Restaurant | None:
        result = await self.db.execute(
            select(Restaurant)
            .options(selectinload(Restaurant.categories))
            .where(Restaurant.id == restaurant_id, Restaurant.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_with_categories(self, restaurant_id: int) -> Restaurant | None:
        result = await self.db.execute(
            select(Restaurant)
            .options(selectinload(Restaurant.categories))
            .where(Restaurant.id == restaurant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_admin_id(self, user_id: int) -> Restaurant | None:
        result = await self.db.execute(
            select(Restaurant)
            .options(selectinload(Restaurant.categories))
            .where(Restaurant.restaurant_admin_id == user_id)
        )
        return result.scalar_one_or_none()

    async def exists_for_admin(self, user_id: int, exclude_id: int | None = None) -> bool:
        stmt = select(Restaurant.id).where(Restaurant.restaurant_admin_id == user_id)
        if exclude_id is not None:
            stmt = stmt.where(Restaurant.id != exclude_id)
        result = await self.db.scalar(stmt)
        return result is not None
