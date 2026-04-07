from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import TokenBlacklist, User
from app.schemas.user import AuthResponse, LoginRequest, RegisterRequest, UserProfileWithAllergens

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


async def _get_user_with_allergens(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(
        select(User).options(selectinload(User.allergens)).where(User.id == user_id)
    )
    return result.scalar_one()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    email_taken = await db.scalar(select(User).where(User.email == body.email))
    if email_taken:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already taken")

    phone_taken = await db.scalar(select(User).where(User.phone == body.phone))
    if phone_taken:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already taken")

    user = User(
        email=body.email,
        phone=body.phone,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    user = await _get_user_with_allergens(db, user.id)
    token = create_access_token(user.id, user.role.value)
    return AuthResponse(access_token=token, user=UserProfileWithAllergens.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")

    user = await _get_user_with_allergens(db, user.id)
    token = create_access_token(user.id, user.role.value)
    return AuthResponse(access_token=token, user=UserProfileWithAllergens.model_validate(user))


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db.add(TokenBlacklist(token=credentials.credentials, user_id=current_user.id))
    await db.commit()
    return {"message": "OK"}


@router.get("/me", response_model=UserProfileWithAllergens)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_user_with_allergens(db, current_user.id)
