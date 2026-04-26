from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import (
    PasswordChangeRequest,
    ProfileUpdateRequest,
    UserProfileWithAllergens,
)
from app.services.profile import ProfileService, get_profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.put("", response_model=UserProfileWithAllergens)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.update_profile(current_user.id, body)


@router.put("/password")
async def change_password(
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    await service.change_password(current_user, body)
    return {"message": "OK"}
