from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.order import OrderCreate, OrderDetail, OrderList
from app.schemas.review import ReviewCreate, ReviewOut
from app.services.order import OrderService, get_order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderDetail, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    return await service.create(current_user, body)


@router.get("", response_model=OrderList)
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    result = await service.list_for_user(current_user.id, page, limit)
    return OrderList(items=result.items, total=result.total, page=result.page, limit=result.limit)


@router.get("/{order_id}", response_model=OrderDetail)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    return await service.get_for_user(current_user.id, order_id)


@router.post("/{order_id}/cancel", response_model=OrderDetail)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    return await service.cancel_for_user(current_user.id, order_id)


@router.post("/{order_id}/review", response_model=ReviewOut)
async def create_order_review(
    order_id: int,
    body: ReviewCreate,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    return await service.create_review(current_user.id, order_id, body)
