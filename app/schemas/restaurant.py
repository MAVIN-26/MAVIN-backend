from typing import Literal

from pydantic import BaseModel

from app.schemas.category import CategoryOut


RestaurantSort = Literal["rating_desc", "rating_asc", "name_asc", "name_desc"]


class RestaurantAdminOut(BaseModel):
    """Compact view of a restaurant's admin user for admin-facing listings."""

    id: int
    first_name: str
    last_name: str
    phone: str
    email: str

    model_config = {"from_attributes": True}


class RestaurantBase(BaseModel):
    id: int
    name: str
    description: str | None = None
    photo_url: str | None = None
    pickup_address: str
    average_rating: float
    review_count: int
    preparation_time_min: int | None = None
    preparation_time_max: int | None = None
    categories: list[CategoryOut] = []

    model_config = {"from_attributes": True}


class RestaurantPublic(RestaurantBase):
    pass


class RestaurantFull(RestaurantBase):
    is_active: bool
    restaurant_admin_id: int | None = None
    # Inline admin details for the site-admin restaurants table.
    # Nullable because the FK is ON DELETE SET NULL.
    restaurant_admin: RestaurantAdminOut | None = None


class RestaurantList(BaseModel):
    items: list[RestaurantPublic]
    total: int
    page: int
    limit: int


class RestaurantAdminList(BaseModel):
    items: list[RestaurantFull]
    total: int
    page: int
    limit: int


class RestaurantOwnerUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    photo_url: str | None = None
    pickup_address: str | None = None
    preparation_time_min: int | None = None
    preparation_time_max: int | None = None


class RestaurantAdminCreate(BaseModel):
    name: str
    pickup_address: str
    restaurant_admin_id: int
    category_ids: list[int] = []
    preparation_time_min: int | None = None
    preparation_time_max: int | None = None


class RestaurantAdminUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    photo_url: str | None = None
    pickup_address: str | None = None
    is_active: bool | None = None
    category_ids: list[int] | None = None
    restaurant_admin_id: int | None = None
    preparation_time_min: int | None = None
    preparation_time_max: int | None = None
