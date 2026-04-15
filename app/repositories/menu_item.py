from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.allergen import Allergen
from app.models.menu_item import MenuItem
from app.repositories.base import BaseRepository


class MenuItemRepository(BaseRepository[MenuItem]):
    model = MenuItem

    async def list_public_filtered(
        self,
        restaurant_id: int,
        max_calories: int | None,
        max_price: float | None,
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
