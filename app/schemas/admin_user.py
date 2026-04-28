from typing import Literal

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserProfileWithAllergens

AdminCreatableRole = Literal["restaurant_admin", "customer"]


class AdminUserCreate(BaseModel):
    email: EmailStr
    phone: str
    password: str
    first_name: str
    last_name: str
    role: AdminCreatableRole


class AdminUserBlock(BaseModel):
    is_blocked: bool


class PaginatedResponseUserProfile(BaseModel):
    items: list[UserProfileWithAllergens]
    total: int
    page: int
    limit: int
    pages: int


class SuccessResponse(BaseModel):
    message: str = "OK"
