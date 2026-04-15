from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

T = TypeVar("T", bound=Base)


@dataclass
class PaginatedResult(Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    limit: int


class BaseRepository(Generic[T]):
    model: type[T]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, id: int) -> T | None:
        return await self.db.get(self.model, id)

    async def list(self) -> Sequence[T]:
        result = await self.db.execute(select(self.model))
        return result.scalars().all()

    async def list_by_ids(self, ids: Sequence[int]) -> Sequence[T]:
        if not ids:
            return []
        result = await self.db.execute(select(self.model).where(self.model.id.in_(ids)))
        return result.scalars().all()

    def add(self, obj: T) -> None:
        self.db.add(obj)

    async def delete(self, obj: T) -> None:
        await self.db.delete(obj)

    async def commit(self) -> None:
        await self.db.commit()

    async def refresh(self, obj: T, attribute_names: list[str] | None = None) -> None:
        await self.db.refresh(obj, attribute_names=attribute_names)
