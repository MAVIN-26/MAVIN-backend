from pydantic import BaseModel


class MenuCategoryOut(BaseModel):
    id: int
    restaurant_id: int
    name: str
    sort_order: int

    model_config = {"from_attributes": True}


class MenuCategoryCreate(BaseModel):
    name: str
    sort_order: int = 0


class MenuCategoryUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
