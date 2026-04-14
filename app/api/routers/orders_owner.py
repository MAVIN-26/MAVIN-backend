from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.order import Order, OrderStatus
from app.models.restaurant import Restaurant
from app.models.user import User
from app.schemas.order import (
    OrderItemOut,
    OrderOwnerDetail,
    OrderOwnerList,
    OrderOwnerListItem,
)
from app.services.ws_manager import manager as ws_manager

router = APIRouter(
    prefix="/owner/orders",
    tags=["owner-orders"],
    dependencies=[Depends(require_role("restaurant_admin"))],
)


async def _get_owner_restaurant_id(db: AsyncSession, user_id: int) -> int:
    restaurant_id = await db.scalar(
        select(Restaurant.id).where(Restaurant.restaurant_admin_id == user_id)
    )
    if restaurant_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    return restaurant_id


async def _get_owner_order(db: AsyncSession, order_id: int, restaurant_id: int) -> Order:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.restaurant_id == restaurant_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


async def _transition_status(
    db: AsyncSession,
    order: Order,
    expected: OrderStatus,
    new_status: OrderStatus,
    message: str,
) -> Order:
    if order.status != expected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Order status must be '{expected.value}'",
        )
    order.status = new_status
    await db.commit()
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
    return order


@router.get("", response_model=OrderOwnerList)
async def list_owner_orders(
    status: OrderStatus | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_owner_restaurant_id(db, current_user.id)

    base = (
        select(Order, User)
        .join(User, User.id == Order.user_id)
        .where(Order.restaurant_id == restaurant_id)
    )
    if status is not None:
        base = base.where(Order.status == status)

    total_query = select(func.count()).select_from(base.subquery())
    total = await db.scalar(total_query)

    result = await db.execute(
        base.order_by(User.is_premium.desc(), Order.created_at)
        .offset((page - 1) * limit)
        .limit(limit)
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
        for order, user in result.all()
    ]
    return OrderOwnerList(items=items, total=total or 0, page=page, limit=limit)


@router.get("/{order_id}", response_model=OrderOwnerDetail)
async def get_owner_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_owner_restaurant_id(db, current_user.id)
    order = await _get_owner_order(db, order_id, restaurant_id)
    customer = await db.get(User, order.user_id)
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
        customer_name=f"{customer.first_name} {customer.last_name}".strip() if customer else "",
        customer_phone=customer.phone if customer else "",
        is_premium=customer.is_premium if customer else False,
        items=[OrderItemOut.model_validate(i) for i in order.items],
    )


@router.post("/{order_id}/accept", response_model=OrderOwnerDetail)
async def accept_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_owner_restaurant_id(db, current_user.id)
    order = await _get_owner_order(db, order_id, restaurant_id)
    await _transition_status(
        db,
        order,
        OrderStatus.created,
        OrderStatus.cooking,
        "Ваш заказ принят и готовится",
    )
    return await get_owner_order(order_id, current_user, db)


@router.post("/{order_id}/ready", response_model=OrderOwnerDetail)
async def mark_ready(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_owner_restaurant_id(db, current_user.id)
    order = await _get_owner_order(db, order_id, restaurant_id)
    await _transition_status(
        db,
        order,
        OrderStatus.cooking,
        OrderStatus.ready_for_pickup,
        "Ваш заказ готов! Можно забирать",
    )
    return await get_owner_order(order_id, current_user, db)


@router.post("/{order_id}/complete", response_model=OrderOwnerDetail)
async def complete_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_owner_restaurant_id(db, current_user.id)
    order = await _get_owner_order(db, order_id, restaurant_id)
    await _transition_status(
        db,
        order,
        OrderStatus.ready_for_pickup,
        OrderStatus.completed,
        "Заказ выдан. Приятного аппетита!",
    )
    return await get_owner_order(order_id, current_user, db)
