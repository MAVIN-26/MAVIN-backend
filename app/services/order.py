from datetime import datetime, timezone
from decimal import Decimal

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.order import Order, OrderItem, OrderStatus
from app.models.promo_code import PromoCode
from app.models.review import Review
from app.models.user import User
from app.repositories.base import PaginatedResult
from app.repositories.cart import CartRepository
from app.repositories.menu_item import MenuItemRepository
from app.repositories.order import OrderRepository
from app.repositories.promo_code import PromoCodeRepository
from app.repositories.restaurant import RestaurantRepository
from app.repositories.review import ReviewRepository
from app.repositories.user import UserRepository
from app.schemas.order import (
    OrderCreate,
    OrderDetail,
    OrderItemOut,
    OrderListItem,
    OrderOwnerDetail,
    OrderOwnerListItem,
)
from app.schemas.review import ReviewCreate
from app.services.ws_manager import manager as ws_manager


class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OrderRepository(db)
        self.carts = CartRepository(db)
        self.menu_items = MenuItemRepository(db)
        self.restaurants = RestaurantRepository(db)
        self.users = UserRepository(db)
        self.promos = PromoCodeRepository(db)
        self.reviews = ReviewRepository(db)

    # ---------- helpers ----------

    async def _load_valid_promo(self, code: str, user_id: int) -> PromoCode:
        promo = await self.promos.find_by_code(code)
        now = datetime.now(timezone.utc)
        if promo is None or not promo.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found"
            )
        if promo.expires_at is not None and promo.expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found"
            )
        if await self.promos.is_used_by(user_id, promo.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found"
            )
        return promo

    async def _build_detail(self, order: Order) -> OrderDetail:
        restaurant = await self.restaurants.get_by_id(order.restaurant_id)
        promo_code_str: str | None = None
        if order.promo_code_id is not None:
            promo = await self.promos.get_by_id(order.promo_code_id)
            if promo is not None:
                promo_code_str = promo.code
        return OrderDetail(
            id=order.id,
            status=order.status,
            pickup_time=order.pickup_time,
            comment=order.comment,
            payment_method=order.payment_method,
            subtotal=order.subtotal,
            discount_percent=order.discount_percent,
            total=order.total,
            promo_code=promo_code_str,
            restaurant_id=order.restaurant_id,
            restaurant_name=restaurant.name if restaurant else "",
            pickup_address=restaurant.pickup_address if restaurant else "",
            created_at=order.created_at,
            items=[OrderItemOut.model_validate(i) for i in order.items],
        )

    async def _build_owner_detail(self, order: Order) -> OrderOwnerDetail:
        customer = await self.users.get_by_id(order.user_id)
        return OrderOwnerDetail(
            id=order.id,
            status=order.status,
            pickup_time=order.pickup_time,
            comment=order.comment,
            payment_method=order.payment_method,
            subtotal=order.subtotal,
            discount_percent=order.discount_percent,
            total=order.total,
            created_at=order.created_at,
            customer_name=(
                f"{customer.first_name} {customer.last_name}".strip() if customer else ""
            ),
            customer_phone=customer.phone if customer else "",
            is_premium=customer.is_premium if customer else False,
            items=[OrderItemOut.model_validate(i) for i in order.items],
        )

    async def _get_owner_restaurant_id(self, user_id: int) -> int:
        restaurant = await self.restaurants.get_by_admin_id(user_id)
        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
            )
        return restaurant.id

    async def _transition(
        self,
        order: Order,
        expected: OrderStatus,
        new_status: OrderStatus,
        message: str,
    ) -> None:
        if order.status != expected:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Order status must be '{expected.value}'",
            )
        order.status = new_status
        await self.repo.commit()
        await ws_manager.send_to_user(
            order.user_id,
            {
                "event": "order_status_changed",
                "data": {
                    "order_id": order.id,
                    "new_status": new_status.value,
                    "message": message,
                },
            },
        )

    # ---------- customer ----------

    async def create(self, user: User, body: OrderCreate) -> OrderDetail:
        cart = await self.carts.get_with_items(user.id)
        if cart is None or not cart.items or cart.restaurant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty"
            )

        menu_ids = [ci.menu_item_id for ci in cart.items]
        menu_items = await self.menu_items.list_by_ids(menu_ids)
        menu_by_id = {mi.id: mi for mi in menu_items}

        subtotal = Decimal("0")
        order_items: list[OrderItem] = []
        for ci in cart.items:
            mi = menu_by_id.get(ci.menu_item_id)
            if mi is None or not mi.is_available:
                name = mi.name if mi else f"Item #{ci.menu_item_id}"
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Item '{name}' is no longer available",
                )
            subtotal += Decimal(mi.price) * ci.quantity
            order_items.append(
                OrderItem(
                    menu_item_id=mi.id,
                    name=mi.name,
                    price=mi.price,
                    quantity=ci.quantity,
                )
            )

        promo: PromoCode | None = None
        promo_discount = 0
        if body.promo_code:
            promo = await self._load_valid_promo(body.promo_code, user.id)
            promo_discount = promo.discount_percent

        subscription_discount = 5 if user.is_premium else 0
        discount_percent = max(promo_discount, subscription_discount)
        total = (subtotal * (100 - discount_percent) / Decimal(100)).quantize(Decimal("0.01"))

        order = Order(
            user_id=user.id,
            restaurant_id=cart.restaurant_id,
            status=OrderStatus.created,
            pickup_time=body.pickup_time,
            comment=body.comment,
            payment_method=body.payment_method,
            subtotal=subtotal.quantize(Decimal("0.01")),
            discount_percent=discount_percent,
            total=total,
            promo_code_id=promo.id if promo else None,
            items=order_items,
        )
        self.repo.add(order)
        await self.db.flush()

        if promo is not None:
            await self.promos.mark_used(user.id, promo.id)

        for ci in list(cart.items):
            await self.carts.delete_item(ci)
        cart.restaurant_id = None

        await self.repo.commit()

        loaded = await self.repo.get_with_items(order.id)
        assert loaded is not None

        restaurant = await self.restaurants.get_by_id(loaded.restaurant_id)
        if restaurant is not None and restaurant.restaurant_admin_id is not None:
            await ws_manager.send_to_user(
                restaurant.restaurant_admin_id,
                {"event": "new_order", "data": {"order_id": loaded.id}},
            )

        return await self._build_detail(loaded)

    async def list_for_user(
        self, user_id: int, page: int, limit: int
    ) -> PaginatedResult[OrderListItem]:
        rows, total = await self.repo.list_for_user_paginated(user_id, page, limit)
        items = [
            OrderListItem(
                id=order.id,
                created_at=order.created_at,
                total=order.total,
                restaurant_id=order.restaurant_id,
                restaurant_name=name,
                status=order.status,
            )
            for order, name in rows
        ]
        return PaginatedResult(items=items, total=total, page=page, limit=limit)

    async def get_for_user(self, user_id: int, order_id: int) -> OrderDetail:
        order = await self.repo.get_for_user(order_id, user_id)
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )
        return await self._build_detail(order)

    async def cancel_for_user(self, user_id: int, order_id: int) -> OrderDetail:
        order = await self.repo.get_for_user(order_id, user_id)
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )
        if order.status != OrderStatus.created:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Order is already being prepared and cannot be cancelled",
            )
        order.status = OrderStatus.cancelled
        await self.repo.commit()

        restaurant = await self.restaurants.get_by_id(order.restaurant_id)
        if restaurant is not None and restaurant.restaurant_admin_id is not None:
            await ws_manager.send_to_user(
                restaurant.restaurant_admin_id,
                {"event": "order_cancelled", "data": {"order_id": order.id}},
            )

        return await self._build_detail(order)

    async def create_review(
        self, user_id: int, order_id: int, body: ReviewCreate
    ) -> Review:
        order = await self.repo.get_by_id(order_id)
        if order is None or order.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )
        if order.status != OrderStatus.completed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Order is not completed",
            )
        if await self.reviews.find_by_order_id(order_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Review already exists"
            )

        review = Review(
            order_id=order_id,
            user_id=user_id,
            restaurant_id=order.restaurant_id,
            rating=body.rating,
        )
        self.reviews.add(review)
        await self.db.flush()

        avg = await self.reviews.average_rating_for_restaurant(order.restaurant_id)
        restaurant = await self.restaurants.get_by_id(order.restaurant_id)
        if restaurant is not None:
            restaurant.average_rating = avg if avg is not None else 0.0

        await self.reviews.commit()
        await self.reviews.refresh(review)
        return review

    # ---------- owner ----------

    async def list_for_owner(
        self,
        user_id: int,
        status_filter: OrderStatus | None,
        page: int,
        limit: int,
    ) -> PaginatedResult[OrderOwnerListItem]:
        restaurant_id = await self._get_owner_restaurant_id(user_id)
        rows, total = await self.repo.list_for_restaurant_paginated(
            restaurant_id, status_filter, page, limit
        )
        items = [
            OrderOwnerListItem(
                id=order.id,
                created_at=order.created_at,
                pickup_time=order.pickup_time,
                status=order.status,
                total=order.total,
                customer_name=f"{user.first_name} {user.last_name}".strip(),
                is_premium=user.is_premium,
            )
            for order, user in rows
        ]
        return PaginatedResult(items=items, total=total, page=page, limit=limit)

    async def _get_owner_order(self, order_id: int, user_id: int) -> Order:
        restaurant_id = await self._get_owner_restaurant_id(user_id)
        order = await self.repo.get_for_restaurant(order_id, restaurant_id)
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )
        return order

    async def get_for_owner(self, user_id: int, order_id: int) -> OrderOwnerDetail:
        order = await self._get_owner_order(order_id, user_id)
        return await self._build_owner_detail(order)

    async def accept(self, user_id: int, order_id: int) -> OrderOwnerDetail:
        order = await self._get_owner_order(order_id, user_id)
        await self._transition(
            order,
            OrderStatus.created,
            OrderStatus.cooking,
            "Ваш заказ принят и готовится",
        )
        return await self._build_owner_detail(order)

    async def mark_ready(self, user_id: int, order_id: int) -> OrderOwnerDetail:
        order = await self._get_owner_order(order_id, user_id)
        await self._transition(
            order,
            OrderStatus.cooking,
            OrderStatus.ready_for_pickup,
            "Ваш заказ готов! Можно забирать",
        )
        return await self._build_owner_detail(order)

    async def complete(self, user_id: int, order_id: int) -> OrderOwnerDetail:
        order = await self._get_owner_order(order_id, user_id)
        await self._transition(
            order,
            OrderStatus.ready_for_pickup,
            OrderStatus.completed,
            "Заказ выдан. Приятного аппетита!",
        )
        return await self._build_owner_detail(order)


def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(db)
