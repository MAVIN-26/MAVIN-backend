from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole
from app.schemas.allergen import AllergenOut

__all__ = [
    "AllergenOut",
    "UserProfile",
    "UserProfileWithAllergens",
    "RegisterRequest",
    "LoginRequest",
    "AuthResponse",
]


class UserProfile(BaseModel):
    id: int
    email: str
    phone: str
    first_name: str
    last_name: str
    role: UserRole
    is_premium: bool
    is_blocked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileWithAllergens(UserProfile):
    allergens: list[AllergenOut] = []


class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str
    password: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileWithAllergens
