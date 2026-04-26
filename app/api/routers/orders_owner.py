from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, require_role
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.order import OrderOwnerDetail, OrderOwnerList
from app.services.order import OrderService, get_order_service

router = APIRouter(
    prefix="/owner/orders",
    tags=["owner-orders"],
    dependencies=[Depends(require_role("restaurant_admin"))],
)


@router.get("", response_model=OrderOwnerList)
async def list_owner_orders(
    status: OrderStatus | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    result = await service.list_for_owner(current_user.id, status, page, limit)
    return OrderOwnerList(
        items=result.items, total=result.total, page=result.page, limit=result.limit
    )


@router.get("/{order_id}", response_model=OrderOwnerDetail)
async def get_owner_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    return await service.get_for_owner(current_user.id, order_id)


@router.post("/{order_id}/accept", response_model=OrderOwnerDetail)
async def accept_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    return await service.accept(current_user.id, order_id)


@router.post("/{order_id}/ready", response_model=OrderOwnerDetail)
async def mark_ready(
    order_id: int,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    return await service.mark_ready(current_user.id, order_id)


@router.post("/{order_id}/complete", response_model=OrderOwnerDetail)
async def complete_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    return await service.complete(current_user.id, order_id)
