from typing import Sequence

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.restaurant import Restaurant
from app.repositories.favorite import FavoriteRepository
from app.repositories.restaurant import RestaurantRepository


class FavoriteService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = FavoriteRepository(db)
        self.restaurants = RestaurantRepository(db)

    async def list_for_user(self, user_id: int) -> Sequence[Restaurant]:
        return await self.repo.list_restaurants_for_user(user_id)

    async def add(self, user_id: int, restaurant_id: int) -> None:
        restaurant = await self.restaurants.get_by_id(restaurant_id)
        if restaurant is None or not restaurant.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )
        existing = await self.repo.find(user_id, restaurant_id)
        if existing is not None:
            return
        await self.repo.add_if_absent(user_id, restaurant_id)

    async def remove(self, user_id: int, restaurant_id: int) -> None:
        favorite = await self.repo.find(user_id, restaurant_id)
        if favorite is not None:
            await self.repo.delete(favorite)
            await self.repo.commit()


def get_favorite_service(db: AsyncSession = Depends(get_db)) -> FavoriteService:
    return FavoriteService(db)
