from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.admin_user import (
    AdminUserBlock,
    AdminUserCreate,
    PaginatedResponseUserProfile,
    SuccessResponse,
)
from app.schemas.user import UserProfileWithAllergens
from app.services.admin_user import AdminUserService, get_admin_user_service

admin_router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(require_role("site_admin"))],
)


@admin_router.get("", response_model=PaginatedResponseUserProfile)
async def admin_list_users(
    search: str | None = Query(None),
    role: UserRole | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    service: AdminUserService = Depends(get_admin_user_service),
):
    result, pages = await service.list(search, role, page, limit)
    return PaginatedResponseUserProfile(
        items=result.items,
        total=result.total,
        page=result.page,
        limit=result.limit,
        pages=pages,
    )


@admin_router.post(
    "",
    response_model=UserProfileWithAllergens,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_user(
    body: AdminUserCreate,
    service: AdminUserService = Depends(get_admin_user_service),
):
    return await service.create(body)


@admin_router.patch("/{user_id}/block", response_model=SuccessResponse)
async def admin_block_user(
    user_id: int,
    body: AdminUserBlock,
    current_user: User = Depends(get_current_user),
    service: AdminUserService = Depends(get_admin_user_service),
):
    await service.set_blocked(user_id, body.is_blocked, current_user.id)
    return SuccessResponse(message="OK")
