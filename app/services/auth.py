from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.repositories.token_blacklist import TokenBlacklistRepository
from app.repositories.user import UserRepository
from app.schemas.user import LoginRequest, RegisterRequest


@dataclass
class AuthResult:
    user: User
    access_token: str


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.users = UserRepository(db)
        self.tokens = TokenBlacklistRepository(db)

    async def register(self, body: RegisterRequest) -> AuthResult:
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
        )
        self.users.add(user)
        await self.users.commit()
        await self.users.refresh(user)

        loaded = await self.users.get_with_allergens(user.id)
        assert loaded is not None
        token = create_access_token(loaded.id, loaded.role.value)
        return AuthResult(user=loaded, access_token=token)

    async def login(self, body: LoginRequest) -> AuthResult:
        user = await self.users.find_by_email(body.email)
        if user is None or not verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if user.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is blocked",
            )

        loaded = await self.users.get_with_allergens(user.id)
        assert loaded is not None
        token = create_access_token(loaded.id, loaded.role.value)
        return AuthResult(user=loaded, access_token=token)

    async def logout(self, token: str, user_id: int) -> None:
        self.tokens.add_token(token, user_id)
        await self.tokens.commit()

    async def me(self, user_id: int) -> User:
        user = await self.users.get_with_allergens(user_id)
        assert user is not None
        return user


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)
