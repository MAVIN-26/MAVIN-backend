from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.allergen import Allergen
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
from app.models.user import User
from app.schemas.menu_item import (
    MenuItemAvailability,
    MenuItemCreate,
    MenuItemOwner,
    MenuItemPublic,
    MenuItemUpdate,
)

public_router = APIRouter(tags=["menu"])
owner_router = APIRouter(
    prefix="/owner/menu",
    tags=["owner-menu"],
    dependencies=[Depends(require_role("restaurant_admin"))],
)


async def _load_allergens(db: AsyncSession, ids: list[int]) -> list[Allergen]:
    if not ids:
        return []
    result = await db.execute(select(Allergen).where(Allergen.id.in_(ids)))
    allergens = result.scalars().all()
    if len(allergens) != len(set(ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid allergen_ids")
    return list(allergens)


async def _get_owner_restaurant_id(db: AsyncSession, user_id: int) -> int:
    restaurant_id = await db.scalar(
        select(Restaurant.id).where(Restaurant.restaurant_admin_id == user_id)
    )
    if restaurant_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    return restaurant_id


async def _get_owner_menu_item(db: AsyncSession, item_id: int, user_id: int) -> MenuItem:
    result = await db.execute(
        select(MenuItem)
        .options(selectinload(MenuItem.allergens))
        .where(MenuItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    owner_id = await db.scalar(
        select(Restaurant.restaurant_admin_id).where(Restaurant.id == item.restaurant_id)
    )
    if owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your menu item")
    return item


def _parse_exclude_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        return [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="exclude_allergen_ids must be a comma-separated list of integers",
        )


@public_router.get("/restaurants/{restaurant_id}/menu", response_model=list[MenuItemPublic])
async def list_public_menu(
    restaurant_id: int,
    max_calories: int | None = Query(None),
    max_price: float | None = Query(None),
    exclude_allergen_ids: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    restaurant_active = await db.scalar(
        select(Restaurant.is_active).where(Restaurant.id == restaurant_id)
    )
    if restaurant_active is None or not restaurant_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    exclude_ids = _parse_exclude_ids(exclude_allergen_ids)

    query = (
        select(MenuItem)
        .options(selectinload(MenuItem.allergens))
        .where(MenuItem.restaurant_id == restaurant_id, MenuItem.is_available.is_(True))
    )
    if max_calories is not None:
        query = query.where(MenuItem.calories <= max_calories)
    if max_price is not None:
        query = query.where(MenuItem.price <= max_price)
    if exclude_ids:
        excluded_item_ids = select(MenuItem.id).join(MenuItem.allergens).where(
            Allergen.id.in_(exclude_ids)
        )
        query = query.where(MenuItem.id.notin_(excluded_item_ids))

    result = await db.execute(query.order_by(MenuItem.id))
    return result.scalars().all()


@owner_router.get("", response_model=list[MenuItemOwner])
async def list_owner_menu(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_owner_restaurant_id(db, current_user.id)
    result = await db.execute(
        select(MenuItem)
        .options(selectinload(MenuItem.allergens))
        .where(MenuItem.restaurant_id == restaurant_id)
        .order_by(MenuItem.id)
    )
    return result.scalars().all()


@owner_router.post("", response_model=MenuItemOwner, status_code=status.HTTP_201_CREATED)
async def create_owner_menu_item(
    body: MenuItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_owner_restaurant_id(db, current_user.id)
    allergens = await _load_allergens(db, body.allergen_ids)

    data = body.model_dump(exclude={"allergen_ids"})
    item = MenuItem(restaurant_id=restaurant_id, allergens=allergens, **data)
    db.add(item)
    await db.commit()

    result = await db.execute(
        select(MenuItem).options(selectinload(MenuItem.allergens)).where(MenuItem.id == item.id)
    )
    return result.scalar_one()


@owner_router.put("/{item_id}", response_model=MenuItemOwner)
async def update_owner_menu_item(
    item_id: int,
    body: MenuItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_owner_menu_item(db, item_id, current_user.id)
    data = body.model_dump(exclude_unset=True)
    allergen_ids = data.pop("allergen_ids", None)

    for field, value in data.items():
        setattr(item, field, value)
    if allergen_ids is not None:
        item.allergens = await _load_allergens(db, allergen_ids)

    await db.commit()

    result = await db.execute(
        select(MenuItem).options(selectinload(MenuItem.allergens)).where(MenuItem.id == item.id)
    )
    return result.scalar_one()


@owner_router.patch("/{item_id}/availability", response_model=MenuItemOwner)
async def set_owner_menu_item_availability(
    item_id: int,
    body: MenuItemAvailability,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_owner_menu_item(db, item_id, current_user.id)
    item.is_available = body.is_available
    await db.commit()
    await db.refresh(item)
    return item


@owner_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_owner_menu_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_owner_menu_item(db, item_id, current_user.id)
    await db.delete(item)
    await db.commit()
