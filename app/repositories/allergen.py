from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.allergen import Allergen
from app.repositories.base import BaseRepository
from app.repositories.exceptions import AlreadyExistsError


class AllergenRepository(BaseRepository[Allergen]):
    model = Allergen

    async def list_sorted(self) -> Sequence[Allergen]:
        result = await self.db.execute(select(Allergen).order_by(Allergen.name))
        return result.scalars().all()

    async def create(self, name: str) -> Allergen:
        allergen = Allergen(name=name)
        self.db.add(allergen)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise AlreadyExistsError()
        await self.db.refresh(allergen)
        return allergen

    async def update_name(self, allergen: Allergen, name: str) -> Allergen:
        allergen.name = name
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise AlreadyExistsError()
        await self.db.refresh(allergen)
        return allergen
