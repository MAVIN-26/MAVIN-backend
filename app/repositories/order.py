from datetime import datetime
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderStatus
from app.models.restaurant import Restaurant
from app.models.user import User
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    model = Order

    async def get_with_items(self, order_id: int) -> Order | None:
        result = await self.db.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_for_user(self, order_id: int, user_id: int) -> Order | None:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id, Order.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_for_restaurant(self, order_id: int, restaurant_id: int) -> Order | None:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id, Order.restaurant_id == restaurant_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user_paginated(
        self, user_id: int, page: int, limit: int
    ) -> tuple[Sequence[tuple[Order, str]], int]:
        total = await self.db.scalar(
            select(func.count(Order.id)).where(Order.user_id == user_id)
        )
        result = await self.db.execute(
            select(Order, Restaurant.name)
            .join(Restaurant, Restaurant.id == Order.restaurant_id)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        rows = [(order, name) for order, name in result.all()]
        return rows, total or 0

    async def list_for_restaurant_paginated(
        self,
        restaurant_id: int,
        status_filter: OrderStatus | None,
        page: int,
        limit: int,
    ) -> tuple[Sequence[tuple[Order, User]], int]:
        base = (
            select(Order, User)
            .join(User, User.id == Order.user_id)
            .where(Order.restaurant_id == restaurant_id)
        )
        if status_filter is not None:
            base = base.where(Order.status == status_filter)

        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))
        result = await self.db.execute(
            base.order_by(User.is_premium.desc(), Order.created_at)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        rows = [(order, user) for order, user in result.all()]
        return rows, total or 0

    async def count_created_since(self, since: datetime) -> int:
        total = await self.db.scalar(
            select(func.count(Order.id)).where(Order.created_at >= since)
        )
        return total or 0

    async def sum_revenue_completed(self) -> float:
        total = await self.db.scalar(
            select(func.coalesce(func.sum(Order.total), 0)).where(
                Order.status == OrderStatus.completed
            )
        )
        return float(total or 0)
