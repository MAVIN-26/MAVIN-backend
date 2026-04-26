from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)


class ReviewOut(BaseModel):
    id: int
    rating: int
    created_at: datetime

    model_config = {"from_attributes": True}
