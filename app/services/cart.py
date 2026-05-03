from decimal import Decimal

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.cart import Cart
from app.repositories.cart import CartRepository
from app.repositories.menu_item import MenuItemRepository
from app.repositories.restaurant import RestaurantRepository
from app.schemas.cart import CartItemCreate, CartItemOut, CartItemUpdate, CartOut


class CartService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = CartRepository(db)
        self.menu_items = MenuItemRepository(db)
        self.restaurants = RestaurantRepository(db)

    async def _get_or_create(self, user_id: int) -> Cart:
        cart = await self.repo.get_with_items(user_id)
        if cart is None:
            new_cart = Cart(user_id=user_id)
            self.repo.add(new_cart)
            await self.repo.commit()
            cart = await self.repo.get_with_items(user_id)
            assert cart is not None
        return cart

    async def _build_out(self, cart: Cart) -> CartOut:
        if not cart.items:
            return CartOut()

        menu_item_ids = [ci.menu_item_id for ci in cart.items]
        menu_items = await self.menu_items.list_by_ids(menu_item_ids)
        menu_by_id = {mi.id: mi for mi in menu_items}

        restaurant_name = None
        if cart.restaurant_id is not None:
            restaurant = await self.restaurants.get_by_id(cart.restaurant_id)
            if restaurant is not None:
                restaurant_name = restaurant.name

        items_out: list[CartItemOut] = []
        subtotal = Decimal("0")
        for ci in cart.items:
            mi = menu_by_id.get(ci.menu_item_id)
            if mi is None:
                continue
            item_subtotal = Decimal(mi.price) * ci.quantity
            items_out.append(
                CartItemOut(
                    id=ci.id,
                    menu_item_id=mi.id,
                    name=mi.name,
                    photo_url=mi.photo_url,
                    price=float(mi.price),
                    quantity=ci.quantity,
                    subtotal=float(item_subtotal),
                )
            )
            subtotal += item_subtotal

        return CartOut(
            restaurant_id=cart.restaurant_id,
            restaurant_name=restaurant_name,
            items=items_out,
            subtotal=float(subtotal),
        )

    async def get(self, user_id: int) -> CartOut:
        cart = await self._get_or_create(user_id)
        return await self._build_out(cart)

    async def add_item(self, user_id: int, body: CartItemCreate) -> CartOut:
        menu_item = await self.menu_items.get_by_id(body.menu_item_id)
        if menu_item is None or not menu_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not available",
            )

        cart = await self._get_or_create(user_id)

        if cart.restaurant_id is not None and cart.restaurant_id != menu_item.restaurant_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Item is from another restaurant. Clear the cart first.",
            )

        if cart.restaurant_id is None:
            cart.restaurant_id = menu_item.restaurant_id

        existing = next((ci for ci in cart.items if ci.menu_item_id == menu_item.id), None)
        if existing is not None:
            existing.quantity += body.quantity
        else:
            self.repo.add_item(cart.id, menu_item.id, body.quantity)

        await self.repo.commit()
        cart = await self.repo.reload_with_items(cart.id)
        return await self._build_out(cart)

    async def update_item(self, user_id: int, item_id: int, body: CartItemUpdate) -> CartOut:
        found = await self.repo.find_user_item(item_id, user_id)
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found",
            )
        item, cart = found
        if body.quantity == 0:
            await self.repo.delete_item(item)
        else:
            item.quantity = body.quantity
        await self.repo.commit()

        cart = await self.repo.reload_with_items(cart.id)
        if not cart.items:
            cart.restaurant_id = None
            await self.repo.commit()
        return await self._build_out(cart)

    async def delete_item(self, user_id: int, item_id: int) -> CartOut:
        found = await self.repo.find_user_item(item_id, user_id)
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found",
            )
        item, cart = found
        await self.repo.delete_item(item)
        await self.repo.commit()

        cart = await self.repo.reload_with_items(cart.id)
        if not cart.items:
            cart.restaurant_id = None
            await self.repo.commit()
        return await self._build_out(cart)

    async def clear(self, user_id: int) -> None:
        cart = await self.repo.get_with_items(user_id)
        if cart is None:
            return
        for ci in list(cart.items):
            await self.repo.delete_item(ci)
        cart.restaurant_id = None
        await self.repo.commit()


def get_cart_service(db: AsyncSession = Depends(get_db)) -> CartService:
    return CartService(db)
