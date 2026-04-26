from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.menu_category import (
    MenuCategoryCreate,
    MenuCategoryOut,
    MenuCategoryUpdate,
)
from app.services.menu_category import MenuCategoryService, get_menu_category_service

public_router = APIRouter(tags=["menu-categories"])
owner_router = APIRouter(
    prefix="/owner/menu-categories",
    tags=["owner-menu-categories"],
    dependencies=[Depends(require_role("restaurant_admin"))],
)


@public_router.get(
    "/restaurants/{restaurant_id}/menu-categories",
    response_model=list[MenuCategoryOut],
)
async def list_public_menu_categories(
    restaurant_id: int,
    service: MenuCategoryService = Depends(get_menu_category_service),
):
    return await service.list_public(restaurant_id)


@owner_router.get("", response_model=list[MenuCategoryOut])
async def list_owner_menu_categories(
    current_user: User = Depends(get_current_user),
    service: MenuCategoryService = Depends(get_menu_category_service),
):
    return await service.list_owner(current_user.id)


@owner_router.post(
    "", response_model=MenuCategoryOut, status_code=status.HTTP_201_CREATED
)
async def create_owner_menu_category(
    body: MenuCategoryCreate,
    current_user: User = Depends(get_current_user),
    service: MenuCategoryService = Depends(get_menu_category_service),
):
    return await service.create_owner(current_user.id, body)


@owner_router.put("/{category_id}", response_model=MenuCategoryOut)
async def update_owner_menu_category(
    category_id: int,
    body: MenuCategoryUpdate,
    current_user: User = Depends(get_current_user),
    service: MenuCategoryService = Depends(get_menu_category_service),
):
    return await service.update_owner(category_id, current_user.id, body)


@owner_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_owner_menu_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    service: MenuCategoryService = Depends(get_menu_category_service),
):
    await service.delete_owner(category_id, current_user.id)
