import math

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.base import PaginatedResult
from app.repositories.user import UserRepository
from app.schemas.admin_user import AdminUserCreate


class AdminUserService:
    def __init__(self, db: AsyncSession) -> None:
        self.users = UserRepository(db)

    async def list(
        self,
        search: str | None,
        role: UserRole | None,
        page: int,
        limit: int,
    ) -> tuple[PaginatedResult[User], int]:
        result = await self.users.list_paginated(search, role, page, limit)
        pages = max(1, math.ceil(result.total / limit)) if result.total else 1
        return result, pages

    async def create(self, body: AdminUserCreate) -> User:
        if await self.users.find_by_email(body.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already taken",
            )
        if await self.users.find_by_phone(body.phone):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone already taken",
            )

        user = User(
            email=body.email,
            phone=body.phone,
            password_hash=hash_password(body.password),
            first_name=body.first_name,
            last_name=body.last_name,
            role=UserRole(body.role),
        )
        self.users.add(user)
        await self.users.commit()

        loaded = await self.users.get_with_allergens(user.id)
        assert loaded is not None
        return loaded

    async def set_blocked(self, user_id: int, is_blocked: bool, current_user_id: int) -> None:
        if user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change block status of the current user",
            )
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        user.is_blocked = is_blocked
        await self.users.commit()


def get_admin_user_service(db: AsyncSession = Depends(get_db)) -> AdminUserService:
    return AdminUserService(db)
