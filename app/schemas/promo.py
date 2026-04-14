from datetime import datetime

from pydantic import BaseModel, Field


class PromoOut(BaseModel):
    id: int
    code: str
    discount_percent: int
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class PromoAdminOut(PromoOut):
    is_active: bool


class PromoList(BaseModel):
    items: list[PromoOut]
    total: int
    page: int
    limit: int


class PromoAdminList(BaseModel):
    items: list[PromoAdminOut]
    total: int
    page: int
    limit: int


class PromoValidateRequest(BaseModel):
    code: str


class PromoCreate(BaseModel):
    code: str
    discount_percent: int = Field(ge=1, le=100)
    expires_at: datetime | None = None


class PromoUpdate(BaseModel):
    is_active: bool | None = None
    discount_percent: int | None = Field(default=None, ge=1, le=100)
    expires_at: datetime | None = None
