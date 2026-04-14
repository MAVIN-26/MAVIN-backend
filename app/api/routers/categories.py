from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

public_router = APIRouter(tags=["categories"])
admin_router = APIRouter(
    prefix="/admin/categories",
    tags=["admin-categories"],
    dependencies=[Depends(require_role("site_admin"))],
)


@public_router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.name))
    return result.scalars().all()


@admin_router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)):
    category = Category(name=body.name)
    db.add(category)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists")
    await db.refresh(category)
    return category


@admin_router.put("/{category_id}", response_model=CategoryOut)
async def update_category(category_id: int, body: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    category.name = body.name
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists")
    await db.refresh(category)
    return category


@admin_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    await db.delete(category)
    await db.commit()
