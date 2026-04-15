from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.favorite import Favorite
from app.models.restaurant import Restaurant
from app.repositories.base import BaseRepository


class FavoriteRepository(BaseRepository[Favorite]):
    model = Favorite

    async def list_restaurants_for_user(self, user_id: int) -> Sequence[Restaurant]:
        result = await self.db.execute(
            select(Restaurant)
            .join(Favorite, Favorite.restaurant_id == Restaurant.id)
            .options(selectinload(Restaurant.categories))
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.id.desc())
        )
        return result.scalars().all()

    async def find(self, user_id: int, restaurant_id: int) -> Favorite | None:
        return await self.db.scalar(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.restaurant_id == restaurant_id,
            )
        )

    async def add_if_absent(self, user_id: int, restaurant_id: int) -> None:
        self.db.add(Favorite(user_id=user_id, restaurant_id=restaurant_id))
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
