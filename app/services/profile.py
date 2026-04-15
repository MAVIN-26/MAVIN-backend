from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.allergen import Allergen
from app.models.user import User
from app.repositories.allergen import AllergenRepository
from app.repositories.user import UserRepository
from app.schemas.user import PasswordChangeRequest, ProfileUpdateRequest


class ProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.users = UserRepository(db)
        self.allergens = AllergenRepository(db)

    async def _load_allergens(self, ids: list[int]) -> list[Allergen]:
        if not ids:
            return []
        allergens = await self.allergens.list_by_ids(ids)
        if len(allergens) != len(set(ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid allergen_ids",
            )
        return list(allergens)

    async def update_profile(self, user_id: int, body: ProfileUpdateRequest) -> User:
        user = await self.users.get_with_allergens(user_id)
        assert user is not None

        data = body.model_dump(exclude_unset=True)
        allergen_ids = data.pop("allergen_ids", None)
        new_email = data.pop("email", None)

        if new_email is not None and new_email != user.email:
            taken = await self.users.find_by_email_excluding(new_email, user.id)
            if taken is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already taken",
                )
            user.email = new_email

        for field, value in data.items():
            setattr(user, field, value)

        if allergen_ids is not None:
            user.allergens = await self._load_allergens(allergen_ids)

        await self.users.commit()

        updated = await self.users.get_with_allergens(user.id)
        assert updated is not None
        return updated

    async def change_password(self, user: User, body: PasswordChangeRequest) -> None:
        if not verify_password(body.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid old password",
            )
        user.password_hash = hash_password(body.new_password)
        await self.users.commit()


def get_profile_service(db: AsyncSession = Depends(get_db)) -> ProfileService:
    return ProfileService(db)
