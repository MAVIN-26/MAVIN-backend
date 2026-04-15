from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.cart import Cart, CartItem
from app.repositories.base import BaseRepository


class CartRepository(BaseRepository[Cart]):
    model = Cart

    async def get_with_items(self, user_id: int) -> Cart | None:
        result = await self.db.execute(
            select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def reload_with_items(self, cart_id: int) -> Cart:
        result = await self.db.execute(
            select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart_id)
        )
        return result.scalar_one()

    async def find_user_item(
        self, item_id: int, user_id: int
    ) -> tuple[CartItem, Cart] | None:
        result = await self.db.execute(
            select(CartItem, Cart)
            .join(Cart, Cart.id == CartItem.cart_id)
            .where(CartItem.id == item_id, Cart.user_id == user_id)
        )
        row = result.first()
        if row is None:
            return None
        return row[0], row[1]

    def add_item(self, cart_id: int, menu_item_id: int, quantity: int) -> CartItem:
        item = CartItem(cart_id=cart_id, menu_item_id=menu_item_id, quantity=quantity)
        self.db.add(item)
        return item

    async def delete_item(self, item: CartItem) -> None:
        await self.db.delete(item)
