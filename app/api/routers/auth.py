from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserProfileWithAllergens,
)
from app.services.auth import AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
):
    result = await service.register(body)
    return AuthResponse(
        access_token=result.access_token,
        user=UserProfileWithAllergens.model_validate(result.user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    result = await service.login(body)
    return AuthResponse(
        access_token=result.access_token,
        user=UserProfileWithAllergens.model_validate(result.user),
    )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    await service.logout(credentials.credentials, current_user.id)
    return {"message": "OK"}


@router.get("/me", response_model=UserProfileWithAllergens)
async def me(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    return await service.me(current_user.id)
