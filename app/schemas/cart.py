from pydantic import BaseModel, Field


class CartItemOut(BaseModel):
    id: int
    menu_item_id: int
    name: str
    photo_url: str | None = None
    price: float
    quantity: int
    subtotal: float


class CartOut(BaseModel):
    restaurant_id: int | None = None
    restaurant_name: str | None = None
    items: list[CartItemOut] = []
    subtotal: float = 0


class CartItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=0)
