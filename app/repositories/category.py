from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.category import Category
from app.repositories.base import BaseRepository
from app.repositories.exceptions import AlreadyExistsError


class CategoryRepository(BaseRepository[Category]):
    model = Category

    async def list_sorted(self) -> Sequence[Category]:
        result = await self.db.execute(select(Category).order_by(Category.name))
        return result.scalars().all()

    async def create(self, name: str) -> Category:
        category = Category(name=name)
        self.db.add(category)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise AlreadyExistsError()
        await self.db.refresh(category)
        return category

    async def update_name(self, category: Category, name: str) -> Category:
        category.name = name
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise AlreadyExistsError()
        await self.db.refresh(category)
        return category
