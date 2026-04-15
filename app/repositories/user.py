from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_with_allergens(self, user_id: int) -> User | None:
        result = await self.db.execute(
            select(User).options(selectinload(User.allergens)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_by_email_excluding(self, email: str, exclude_user_id: int) -> User | None:
        return await self.db.scalar(
            select(User).where(User.email == email, User.id != exclude_user_id)
        )
