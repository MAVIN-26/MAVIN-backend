from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.restaurant import (
    RestaurantAdminCreate,
    RestaurantAdminList,
    RestaurantAdminUpdate,
    RestaurantFull,
    RestaurantList,
    RestaurantOwnerUpdate,
    RestaurantPublic,
)
from app.services.restaurant import RestaurantService, get_restaurant_service

public_router = APIRouter(tags=["restaurants"])
owner_router = APIRouter(
    prefix="/owner/restaurant",
    tags=["owner-restaurant"],
    dependencies=[Depends(require_role("restaurant_admin"))],
)
admin_router = APIRouter(
    prefix="/admin/restaurants",
    tags=["admin-restaurants"],
    dependencies=[Depends(require_role("site_admin"))],
)


@public_router.get("/restaurants", response_model=RestaurantList)
async def list_restaurants(
    category_id: int | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    service: RestaurantService = Depends(get_restaurant_service),
):
    result = await service.list_public(category_id, search, page, limit)
    return RestaurantList(items=result.items, total=result.total, page=result.page, limit=result.limit)


@public_router.get("/restaurants/{restaurant_id}", response_model=RestaurantPublic)
async def get_restaurant(
    restaurant_id: int,
    service: RestaurantService = Depends(get_restaurant_service),
):
    return await service.get_public(restaurant_id)


@owner_router.get("", response_model=RestaurantFull)
async def get_owner_restaurant(
    current_user: User = Depends(get_current_user),
    service: RestaurantService = Depends(get_restaurant_service),
):
    return await service.get_owner(current_user.id)


@owner_router.put("", response_model=RestaurantFull)
async def update_owner_restaurant(
    body: RestaurantOwnerUpdate,
    current_user: User = Depends(get_current_user),
    service: RestaurantService = Depends(get_restaurant_service),
):
    return await service.update_owner(current_user.id, body)


@admin_router.get("", response_model=RestaurantAdminList)
async def admin_list_restaurants(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    service: RestaurantService = Depends(get_restaurant_service),
):
    result = await service.list_admin(page, limit)
    return RestaurantAdminList(items=result.items, total=result.total, page=result.page, limit=result.limit)


@admin_router.post("", response_model=RestaurantFull, status_code=status.HTTP_201_CREATED)
async def admin_create_restaurant(
    body: RestaurantAdminCreate,
    service: RestaurantService = Depends(get_restaurant_service),
):
    return await service.create_admin(body)


@admin_router.put("/{restaurant_id}", response_model=RestaurantFull)
async def admin_update_restaurant(
    restaurant_id: int,
    body: RestaurantAdminUpdate,
    service: RestaurantService = Depends(get_restaurant_service),
):
    return await service.update_admin(restaurant_id, body)


@admin_router.delete("/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_restaurant(
    restaurant_id: int,
    service: RestaurantService = Depends(get_restaurant_service),
):
    await service.delete_admin(restaurant_id)
