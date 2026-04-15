from fastapi import APIRouter, Depends, status

from app.api.deps import require_role
from app.schemas.allergen import AllergenCreate, AllergenOut, AllergenUpdate
from app.services.allergen import AllergenService, get_allergen_service

public_router = APIRouter(tags=["allergens"])
admin_router = APIRouter(
    prefix="/admin/allergens",
    tags=["admin-allergens"],
    dependencies=[Depends(require_role("site_admin"))],
)


@public_router.get("/allergens", response_model=list[AllergenOut])
async def list_allergens(service: AllergenService = Depends(get_allergen_service)):
    return await service.list()


@admin_router.post("", response_model=AllergenOut, status_code=status.HTTP_201_CREATED)
async def create_allergen(
    body: AllergenCreate,
    service: AllergenService = Depends(get_allergen_service),
):
    return await service.create(body.name)


@admin_router.put("/{allergen_id}", response_model=AllergenOut)
async def update_allergen(
    allergen_id: int,
    body: AllergenUpdate,
    service: AllergenService = Depends(get_allergen_service),
):
    return await service.update(allergen_id, body.name)


@admin_router.delete("/{allergen_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_allergen(
    allergen_id: int,
    service: AllergenService = Depends(get_allergen_service),
):
    await service.delete(allergen_id)
