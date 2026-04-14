from pydantic import BaseModel, Field


class AIRecommendRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    restaurant_id: int


class AIRecommendationOut(BaseModel):
    ai_text: str
    recommended_dish_ids: list[int]
