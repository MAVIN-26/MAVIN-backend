from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.favorite import Favorite
from app.models.restaurant import Restaurant
from app.models.user import User
from app.schemas.restaurant import RestaurantPublic

router = APIRouter(
    prefix="/favorites",
    tags=["favorites"],
    dependencies=[Depends(require_role("customer"))],
)


@router.get("", response_model=list[RestaurantPublic])
async def list_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Restaurant)
        .join(Favorite, Favorite.restaurant_id == Restaurant.id)
        .options(selectinload(Restaurant.categories))
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.id.desc())
    )
    return result.scalars().all()


@router.post("/{rest_id}")
async def add_favorite(
    rest_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant = await db.get(Restaurant, rest_id)
    if restaurant is None or not restaurant.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    existing = await db.scalar(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.restaurant_id == rest_id,
        )
    )
    if existing is not None:
        return {"message": "OK"}

    db.add(Favorite(user_id=current_user.id, restaurant_id=rest_id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
    return {"message": "OK"}


@router.delete("/{rest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    rest_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    favorite = await db.scalar(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.restaurant_id == rest_id,
        )
    )
    if favorite is not None:
        await db.delete(favorite)
        await db.commit()
