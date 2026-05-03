from sqlalchemy import func, select

from app.models.review import Review
from app.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    model = Review

    async def find_by_order_id(self, order_id: int) -> Review | None:
        return await self.db.scalar(select(Review).where(Review.order_id == order_id))

    async def average_rating_for_restaurant(self, restaurant_id: int) -> float | None:
        avg = await self.db.scalar(
            select(func.avg(Review.rating)).where(Review.restaurant_id == restaurant_id)
        )
        return float(avg) if avg is not None else None

    async def count_for_restaurant(self, restaurant_id: int) -> int:
        result = await self.db.scalar(
            select(func.count(Review.id)).where(Review.restaurant_id == restaurant_id)
        )
        return int(result or 0)
