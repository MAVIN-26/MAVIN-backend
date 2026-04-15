from typing import Sequence

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.allergen import Allergen
from app.repositories.allergen import AllergenRepository
from app.repositories.exceptions import AlreadyExistsError


class AllergenService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AllergenRepository(db)

    async def list(self) -> Sequence[Allergen]:
        return await self.repo.list_sorted()

    async def create(self, name: str) -> Allergen:
        try:
            return await self.repo.create(name)
        except AlreadyExistsError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Allergen already exists",
            )

    async def update(self, allergen_id: int, name: str) -> Allergen:
        allergen = await self.repo.get_by_id(allergen_id)
        if allergen is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Allergen not found",
            )
        try:
            return await self.repo.update_name(allergen, name)
        except AlreadyExistsError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Allergen already exists",
            )

    async def delete(self, allergen_id: int) -> None:
        allergen = await self.repo.get_by_id(allergen_id)
        if allergen is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Allergen not found",
            )
        await self.repo.delete(allergen)
        await self.repo.commit()


def get_allergen_service(db: AsyncSession = Depends(get_db)) -> AllergenService:
    return AllergenService(db)
