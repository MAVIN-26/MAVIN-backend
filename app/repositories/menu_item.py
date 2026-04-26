from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.allergen import Allergen
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderItem
from app.repositories.base import BaseRepository


class MenuItemRepository(BaseRepository[MenuItem]):
    model = MenuItem

    async def list_public_filtered(
        self,
        restaurant_id: int,
        max_calories: int | None,
        max_price: float | None,
        max_proteins: float | None,
        max_fats: float | None,
        max_carbs: float | None,
        exclude_allergen_ids: Sequence[int],
    ) -> Sequence[MenuItem]:
        query = (
            select(MenuItem)
            .options(selectinload(MenuItem.allergens))
            .where(
                MenuItem.restaurant_id == restaurant_id,
                MenuItem.is_available.is_(True),
            )
        )
        if max_calories is not None:
            query = query.where(MenuItem.calories <= max_calories)
        if max_price is not None:
            query = query.where(MenuItem.price <= max_price)
        if max_proteins is not None:
            query = query.where(MenuItem.proteins <= max_proteins)
        if max_fats is not None:
            query = query.where(MenuItem.fats <= max_fats)
        if max_carbs is not None:
            query = query.where(MenuItem.carbs <= max_carbs)
        if exclude_allergen_ids:
            excluded_item_ids = (
                select(MenuItem.id)
                .join(MenuItem.allergens)
                .where(Allergen.id.in_(exclude_allergen_ids))
            )
            query = query.where(MenuItem.id.notin_(excluded_item_ids))

        result = await self.db.execute(query.order_by(MenuItem.id))
        return result.scalars().all()

    async def list_by_restaurant(self, restaurant_id: int) -> Sequence[MenuItem]:
        result = await self.db.execute(
            select(MenuItem)
            .options(selectinload(MenuItem.allergens))
            .where(MenuItem.restaurant_id == restaurant_id)
            .order_by(MenuItem.id)
        )
        return result.scalars().all()

    async def get_with_allergens(self, item_id: int) -> MenuItem | None:
        result = await self.db.execute(
            select(MenuItem)
            .options(selectinload(MenuItem.allergens))
            .where(MenuItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def list_user_choice(
        self,
        restaurant_id: int,
        top_n: int,
        period_days: int,
    ) -> Sequence[MenuItem]:
        """Top-N available menu items for restaurant ranked by order count over period."""
        since = datetime.now(timezone.utc) - timedelta(days=period_days)

        ranked_ids_stmt = (
            select(
                OrderItem.menu_item_id.label("mid"),
                func.sum(OrderItem.quantity).label("cnt"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.restaurant_id == restaurant_id,
                Order.created_at >= since,
                OrderItem.menu_item_id.is_not(None),
            )
            .group_by(OrderItem.menu_item_id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(top_n)
        ).subquery()

        result = await self.db.execute(
            select(MenuItem)
            .options(selectinload(MenuItem.allergens))
            .join(ranked_ids_stmt, ranked_ids_stmt.c.mid == MenuItem.id)
            .where(
                MenuItem.restaurant_id == restaurant_id,
                MenuItem.is_available.is_(True),
            )
            .order_by(ranked_ids_stmt.c.cnt.desc(), MenuItem.id)
        )
        return result.scalars().all()
