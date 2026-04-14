from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.allergen import Allergen
from app.schemas.allergen import AllergenCreate, AllergenOut, AllergenUpdate

public_router = APIRouter(tags=["allergens"])
admin_router = APIRouter(
    prefix="/admin/allergens",
    tags=["admin-allergens"],
    dependencies=[Depends(require_role("site_admin"))],
)


@public_router.get("/allergens", response_model=list[AllergenOut])
async def list_allergens(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Allergen).order_by(Allergen.name))
    return result.scalars().all()


@admin_router.post("", response_model=AllergenOut, status_code=status.HTTP_201_CREATED)
async def create_allergen(body: AllergenCreate, db: AsyncSession = Depends(get_db)):
    allergen = Allergen(name=body.name)
    db.add(allergen)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Allergen already exists")
    await db.refresh(allergen)
    return allergen


@admin_router.put("/{allergen_id}", response_model=AllergenOut)
async def update_allergen(allergen_id: int, body: AllergenUpdate, db: AsyncSession = Depends(get_db)):
    allergen = await db.get(Allergen, allergen_id)
    if allergen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allergen not found")
    allergen.name = body.name
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Allergen already exists")
    await db.refresh(allergen)
    return allergen


@admin_router.delete("/{allergen_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_allergen(allergen_id: int, db: AsyncSession = Depends(get_db)):
    allergen = await db.get(Allergen, allergen_id)
    if allergen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allergen not found")
    await db.delete(allergen)
    await db.commit()
