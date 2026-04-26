from typing import Sequence

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.category import Category
from app.repositories.category import CategoryRepository
from app.repositories.exceptions import AlreadyExistsError


class CategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = CategoryRepository(db)

    async def list(self) -> Sequence[Category]:
        return await self.repo.list_sorted()

    async def create(self, name: str) -> Category:
        try:
            return await self.repo.create(name)
        except AlreadyExistsError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category already exists",
            )

    async def update(self, category_id: int, name: str) -> Category:
        category = await self.repo.get_by_id(category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )
        try:
            return await self.repo.update_name(category, name)
        except AlreadyExistsError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category already exists",
            )

    async def delete(self, category_id: int) -> None:
        category = await self.repo.get_by_id(category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )
        await self.repo.delete(category)
        await self.repo.commit()


def get_category_service(db: AsyncSession = Depends(get_db)) -> CategoryService:
    return CategoryService(db)
