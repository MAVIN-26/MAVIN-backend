from fastapi import APIRouter, Depends, status

from app.api.deps import require_role
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.services.category import CategoryService, get_category_service

public_router = APIRouter(tags=["categories"])
admin_router = APIRouter(
    prefix="/admin/categories",
    tags=["admin-categories"],
    dependencies=[Depends(require_role("site_admin"))],
)


@public_router.get("/categories", response_model=list[CategoryOut])
async def list_categories(service: CategoryService = Depends(get_category_service)):
    return await service.list()


@admin_router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
):
    return await service.create(body.name)


@admin_router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    service: CategoryService = Depends(get_category_service),
):
    return await service.update(category_id, body.name)


@admin_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
):
    await service.delete(category_id)
