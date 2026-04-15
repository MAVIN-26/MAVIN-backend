from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.promo import (
    PromoAdminList,
    PromoAdminOut,
    PromoCreate,
    PromoList,
    PromoOut,
    PromoUpdate,
    PromoValidateRequest,
)
from app.services.promo import PromoService, get_promo_service

customer_router = APIRouter(
    prefix="/promo",
    tags=["promo"],
    dependencies=[Depends(require_role("customer"))],
)
admin_router = APIRouter(
    prefix="/admin/promo",
    tags=["admin-promo"],
    dependencies=[Depends(require_role("site_admin"))],
)


@customer_router.get("", response_model=PromoList)
async def list_active_promos(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    service: PromoService = Depends(get_promo_service),
):
    result = await service.list_active(page, limit)
    return PromoList(items=result.items, total=result.total, page=result.page, limit=result.limit)


@customer_router.post("/validate", response_model=PromoOut)
async def validate_promo(
    body: PromoValidateRequest,
    current_user: User = Depends(get_current_user),
    service: PromoService = Depends(get_promo_service),
):
    return await service.validate(current_user.id, body.code)


@admin_router.get("", response_model=PromoAdminList)
async def admin_list_promos(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    service: PromoService = Depends(get_promo_service),
):
    result = await service.list_admin(page, limit)
    return PromoAdminList(items=result.items, total=result.total, page=result.page, limit=result.limit)


@admin_router.post("", response_model=PromoAdminOut, status_code=status.HTTP_201_CREATED)
async def admin_create_promo(
    body: PromoCreate,
    service: PromoService = Depends(get_promo_service),
):
    return await service.create_admin(body)


@admin_router.put("/{promo_id}", response_model=PromoAdminOut)
async def admin_update_promo(
    promo_id: int,
    body: PromoUpdate,
    service: PromoService = Depends(get_promo_service),
):
    return await service.update_admin(promo_id, body)


@admin_router.delete("/{promo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_promo(
    promo_id: int,
    service: PromoService = Depends(get_promo_service),
):
    await service.delete_admin(promo_id)
