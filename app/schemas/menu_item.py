from decimal import Decimal

from pydantic import BaseModel

from app.schemas.allergen import AllergenOut


class MenuItemBase(BaseModel):
    id: int
    name: str
    description: str | None = None
    photo_url: str | None = None
    price: Decimal
    calories: int | None = None
    proteins: float | None = None
    fats: float | None = None
    carbs: float | None = None
    allergens: list[AllergenOut] = []

    model_config = {"from_attributes": True}


class MenuItemPublic(MenuItemBase):
    pass


class MenuItemOwner(MenuItemBase):
    is_available: bool


class MenuItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: Decimal
    photo_url: str | None = None
    calories: int | None = None
    proteins: float | None = None
    fats: float | None = None
    carbs: float | None = None
    allergen_ids: list[int] = []


class MenuItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    photo_url: str | None = None
    calories: int | None = None
    proteins: float | None = None
    fats: float | None = None
    carbs: float | None = None
    allergen_ids: list[int] | None = None


class MenuItemAvailability(BaseModel):
    is_available: bool
