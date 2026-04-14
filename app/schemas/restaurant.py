from pydantic import BaseModel

from app.schemas.category import CategoryOut


class RestaurantBase(BaseModel):
    id: int
    name: str
    description: str | None = None
    photo_url: str | None = None
    pickup_address: str
    average_rating: float
    categories: list[CategoryOut] = []

    model_config = {"from_attributes": True}


class RestaurantPublic(RestaurantBase):
    pass


class RestaurantFull(RestaurantBase):
    is_active: bool
    restaurant_admin_id: int | None = None


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


class RestaurantAdminCreate(BaseModel):
    name: str
    pickup_address: str
    restaurant_admin_id: int
    category_ids: list[int] = []


class RestaurantAdminUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    photo_url: str | None = None
    pickup_address: str | None = None
    is_active: bool | None = None
    category_ids: list[int] | None = None
    restaurant_admin_id: int | None = None
