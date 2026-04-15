from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.menu_item import (
    MenuItemAvailability,
    MenuItemCreate,
    MenuItemOwner,
    MenuItemPublic,
    MenuItemUpdate,
)
from app.services.menu_item import MenuItemService, get_menu_item_service

public_router = APIRouter(tags=["menu"])
owner_router = APIRouter(
    prefix="/owner/menu",
    tags=["owner-menu"],
    dependencies=[Depends(require_role("restaurant_admin"))],
)


@public_router.get("/restaurants/{restaurant_id}/menu", response_model=list[MenuItemPublic])
async def list_public_menu(
    restaurant_id: int,
    max_calories: int | None = Query(None),
    max_price: float | None = Query(None),
    exclude_allergen_ids: str | None = Query(None),
    service: MenuItemService = Depends(get_menu_item_service),
):
    return await service.list_public(restaurant_id, max_calories, max_price, exclude_allergen_ids)


@owner_router.get("", response_model=list[MenuItemOwner])
async def list_owner_menu(
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
):
    return await service.list_owner(current_user.id)


@owner_router.post("", response_model=MenuItemOwner, status_code=status.HTTP_201_CREATED)
async def create_owner_menu_item(
    body: MenuItemCreate,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
):
    return await service.create_owner(current_user.id, body)


@owner_router.put("/{item_id}", response_model=MenuItemOwner)
async def update_owner_menu_item(
    item_id: int,
    body: MenuItemUpdate,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
):
    return await service.update_owner(item_id, current_user.id, body)


@owner_router.patch("/{item_id}/availability", response_model=MenuItemOwner)
async def set_owner_menu_item_availability(
    item_id: int,
    body: MenuItemAvailability,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
):
    return await service.set_availability(item_id, current_user.id, body)


@owner_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_owner_menu_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
):
    await service.delete_owner(item_id, current_user.id)
