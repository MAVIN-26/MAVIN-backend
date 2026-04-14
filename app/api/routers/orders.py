from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.cart import Cart, CartItem
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderItem, OrderStatus
from app.models.promo_code import PromoCode, used_promo_codes
from app.models.restaurant import Restaurant
from app.models.user import User
from app.schemas.order import (
    OrderCreate,
    OrderDetail,
    OrderItemOut,
    OrderList,
    OrderListItem,
)
from app.services.ws_manager import manager as ws_manager

router = APIRouter(prefix="/orders", tags=["orders"])


async def _load_valid_promo(db: AsyncSession, code: str, user_id: int) -> PromoCode:
    promo = await db.scalar(select(PromoCode).where(PromoCode.code == code))
    now = datetime.now(timezone.utc)
    if promo is None or not promo.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")
    if promo.expires_at is not None and promo.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")
    already = await db.scalar(
        select(used_promo_codes).where(
            used_promo_codes.c.user_id == user_id,
            used_promo_codes.c.promo_code_id == promo.id,
        )
    )
    if already is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")
    return promo


async def _build_order_detail(db: AsyncSession, order: Order) -> OrderDetail:
    restaurant = await db.get(Restaurant, order.restaurant_id)
    promo_code_str = None
    if order.promo_code_id is not None:
        promo_code_str = await db.scalar(
            select(PromoCode.code).where(PromoCode.id == order.promo_code_id)
        )
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


@router.post("", response_model=OrderDetail, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart_result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == current_user.id)
    )
    cart = cart_result.scalar_one_or_none()
    if cart is None or not cart.items or cart.restaurant_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    menu_ids = [ci.menu_item_id for ci in cart.items]
    menu_result = await db.execute(select(MenuItem).where(MenuItem.id.in_(menu_ids)))
    menu_by_id = {mi.id: mi for mi in menu_result.scalars().all()}

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
            OrderItem(menu_item_id=mi.id, name=mi.name, price=mi.price, quantity=ci.quantity)
        )

    promo: PromoCode | None = None
    promo_discount = 0
    if body.promo_code:
        promo = await _load_valid_promo(db, body.promo_code, current_user.id)
        promo_discount = promo.discount_percent

    subscription_discount = 5 if current_user.is_premium else 0
    discount_percent = max(promo_discount, subscription_discount)
    total = (subtotal * (100 - discount_percent) / Decimal(100)).quantize(Decimal("0.01"))

    order = Order(
        user_id=current_user.id,
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
    db.add(order)
    await db.flush()

    if promo is not None:
        await db.execute(
            insert(used_promo_codes).values(user_id=current_user.id, promo_code_id=promo.id)
        )

    for ci in list(cart.items):
        await db.delete(ci)
    cart.restaurant_id = None

    await db.commit()

    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    order = result.scalar_one()

    owner_id = await db.scalar(
        select(Restaurant.restaurant_admin_id).where(Restaurant.id == order.restaurant_id)
    )
    if owner_id is not None:
        await ws_manager.send_to_user(owner_id, {"event": "new_order", "data": {"order_id": order.id}})

    return await _build_order_detail(db, order)


@router.get("", response_model=OrderList)
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(
        select(func.count(Order.id)).where(Order.user_id == current_user.id)
    )
    result = await db.execute(
        select(Order, Restaurant.name)
        .join(Restaurant, Restaurant.id == Order.restaurant_id)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = [
        OrderListItem(
            id=order.id,
            created_at=order.created_at,
            total=order.total,
            restaurant_id=order.restaurant_id,
            restaurant_name=restaurant_name,
            status=order.status,
        )
        for order, restaurant_name in result.all()
    ]
    return OrderList(items=items, total=total or 0, page=page, limit=limit)


@router.get("/{order_id}", response_model=OrderDetail)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return await _build_order_detail(db, order)


@router.post("/{order_id}/cancel", response_model=OrderDetail)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != OrderStatus.created:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Order is already being prepared and cannot be cancelled",
        )
    order.status = OrderStatus.cancelled
    await db.commit()

    owner_id = await db.scalar(
        select(Restaurant.restaurant_admin_id).where(Restaurant.id == order.restaurant_id)
    )
    if owner_id is not None:
        await ws_manager.send_to_user(
            owner_id,
            {"event": "order_cancelled", "data": {"order_id": order.id}},
        )

    return await _build_order_detail(db, order)
