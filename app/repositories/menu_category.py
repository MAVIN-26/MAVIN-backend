from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.menu_category import MenuCategory
from app.repositories.base import BaseRepository
from app.repositories.exceptions import AlreadyExistsError


class MenuCategoryRepository(BaseRepository[MenuCategory]):
    model = MenuCategory

    async def list_by_restaurant(self, restaurant_id: int) -> Sequence[MenuCategory]:
        result = await self.db.execute(
            select(MenuCategory)
            .where(MenuCategory.restaurant_id == restaurant_id)
            .order_by(MenuCategory.sort_order, MenuCategory.id)
        )
        return result.scalars().all()

    async def create(
        self, restaurant_id: int, name: str, sort_order: int = 0
    ) -> MenuCategory:
        category = MenuCategory(
            restaurant_id=restaurant_id, name=name, sort_order=sort_order
        )
        self.db.add(category)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise AlreadyExistsError()
        await self.db.refresh(category)
        return category

    async def update(
        self,
        category: MenuCategory,
        name: str | None,
        sort_order: int | None,
    ) -> MenuCategory:
        if name is not None:
            category.name = name
        if sort_order is not None:
            category.sort_order = sort_order
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise AlreadyExistsError()
        await self.db.refresh(category)
        return category
