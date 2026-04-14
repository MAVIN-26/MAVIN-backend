from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.allergen import Allergen
from app.models.user import User
from app.schemas.user import (
    PasswordChangeRequest,
    ProfileUpdateRequest,
    UserProfileWithAllergens,
)

router = APIRouter(prefix="/profile", tags=["profile"])


async def _load_allergens(db: AsyncSession, ids: list[int]) -> list[Allergen]:
    if not ids:
        return []
    result = await db.execute(select(Allergen).where(Allergen.id.in_(ids)))
    allergens = result.scalars().all()
    if len(allergens) != len(set(ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid allergen_ids")
    return list(allergens)


@router.put("", response_model=UserProfileWithAllergens)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.allergens)).where(User.id == current_user.id)
    )
    user = result.scalar_one()

    data = body.model_dump(exclude_unset=True)
    allergen_ids = data.pop("allergen_ids", None)
    new_email = data.pop("email", None)

    if new_email is not None and new_email != user.email:
        taken = await db.scalar(select(User).where(User.email == new_email, User.id != user.id))
        if taken is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already taken")
        user.email = new_email

    for field, value in data.items():
        setattr(user, field, value)

    if allergen_ids is not None:
        user.allergens = await _load_allergens(db, allergen_ids)

    await db.commit()

    result = await db.execute(
        select(User).options(selectinload(User.allergens)).where(User.id == user.id)
    )
    return result.scalar_one()


@router.put("/password")
async def change_password(
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid old password"
        )
    current_user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "OK"}
