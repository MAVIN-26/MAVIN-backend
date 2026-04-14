from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.category import Category
from app.models.restaurant import Restaurant
from app.models.user import User, UserRole
from app.schemas.restaurant import (
    RestaurantAdminCreate,
    RestaurantAdminList,
    RestaurantAdminUpdate,
    RestaurantFull,
    RestaurantList,
    RestaurantOwnerUpdate,
    RestaurantPublic,
)

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


async def _load_categories(db: AsyncSession, ids: list[int]) -> list[Category]:
    if not ids:
        return []
    result = await db.execute(select(Category).where(Category.id.in_(ids)))
    categories = result.scalars().all()
    if len(categories) != len(set(ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category_ids")
    return list(categories)


@public_router.get("/restaurants", response_model=RestaurantList)
async def list_restaurants(
    category_id: int | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    base = select(Restaurant).where(Restaurant.is_active.is_(True))
    if category_id is not None:
        base = base.join(Restaurant.categories).where(Category.id == category_id)
    if search:
        base = base.where(Restaurant.name.ilike(f"%{search}%"))

    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    result = await db.execute(
        base.options(selectinload(Restaurant.categories))
        .order_by(Restaurant.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = result.unique().scalars().all()
    return RestaurantList(items=items, total=total or 0, page=page, limit=limit)


@public_router.get("/restaurants/{restaurant_id}", response_model=RestaurantPublic)
async def get_restaurant(restaurant_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Restaurant)
        .options(selectinload(Restaurant.categories))
        .where(Restaurant.id == restaurant_id, Restaurant.is_active.is_(True))
    )
    restaurant = result.scalar_one_or_none()
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    return restaurant


async def _get_owner_restaurant(db: AsyncSession, user_id: int) -> Restaurant:
    result = await db.execute(
        select(Restaurant)
        .options(selectinload(Restaurant.categories))
        .where(Restaurant.restaurant_admin_id == user_id)
    )
    restaurant = result.scalar_one_or_none()
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    return restaurant


@owner_router.get("", response_model=RestaurantFull)
async def get_owner_restaurant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_owner_restaurant(db, current_user.id)


@owner_router.put("", response_model=RestaurantFull)
async def update_owner_restaurant(
    body: RestaurantOwnerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant = await _get_owner_restaurant(db, current_user.id)
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(restaurant, field, value)
    await db.commit()
    await db.refresh(restaurant)
    return await _get_owner_restaurant(db, current_user.id)


@admin_router.get("", response_model=RestaurantAdminList)
async def admin_list_restaurants(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count(Restaurant.id)))
    result = await db.execute(
        select(Restaurant)
        .options(selectinload(Restaurant.categories))
        .order_by(Restaurant.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = result.scalars().all()
    return RestaurantAdminList(items=items, total=total or 0, page=page, limit=limit)


@admin_router.post("", response_model=RestaurantFull, status_code=status.HTTP_201_CREATED)
async def admin_create_restaurant(body: RestaurantAdminCreate, db: AsyncSession = Depends(get_db)):
    owner = await db.get(User, body.restaurant_admin_id)
    if owner is None or owner.role != UserRole.restaurant_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="restaurant_admin_id must reference a user with role restaurant_admin",
        )
    existing = await db.scalar(
        select(Restaurant).where(Restaurant.restaurant_admin_id == body.restaurant_admin_id)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This restaurant admin already owns a restaurant",
        )
    categories = await _load_categories(db, body.category_ids)

    restaurant = Restaurant(
        name=body.name,
        pickup_address=body.pickup_address,
        restaurant_admin_id=body.restaurant_admin_id,
        categories=categories,
    )
    db.add(restaurant)
    await db.commit()

    result = await db.execute(
        select(Restaurant)
        .options(selectinload(Restaurant.categories))
        .where(Restaurant.id == restaurant.id)
    )
    return result.scalar_one()


@admin_router.put("/{restaurant_id}", response_model=RestaurantFull)
async def admin_update_restaurant(
    restaurant_id: int, body: RestaurantAdminUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Restaurant)
        .options(selectinload(Restaurant.categories))
        .where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    data = body.model_dump(exclude_unset=True)
    category_ids = data.pop("category_ids", None)
    new_admin_id = data.pop("restaurant_admin_id", None)

    if new_admin_id is not None and new_admin_id != restaurant.restaurant_admin_id:
        owner = await db.get(User, new_admin_id)
        if owner is None or owner.role != UserRole.restaurant_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="restaurant_admin_id must reference a user with role restaurant_admin",
            )
        existing = await db.scalar(
            select(Restaurant).where(
                Restaurant.restaurant_admin_id == new_admin_id,
                Restaurant.id != restaurant_id,
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This restaurant admin already owns a restaurant",
            )
        restaurant.restaurant_admin_id = new_admin_id

    for field, value in data.items():
        setattr(restaurant, field, value)

    if category_ids is not None:
        restaurant.categories = await _load_categories(db, category_ids)

    await db.commit()

    result = await db.execute(
        select(Restaurant)
        .options(selectinload(Restaurant.categories))
        .where(Restaurant.id == restaurant_id)
    )
    return result.scalar_one()


@admin_router.delete("/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_restaurant(restaurant_id: int, db: AsyncSession = Depends(get_db)):
    restaurant = await db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    await db.delete(restaurant)
    await db.commit()
