from datetime import datetime

from pydantic import BaseModel


class SubscriptionPlanOut(BaseModel):
    id: int
    name: str
    price: float
    duration_days: int
    features: list[str] = []

    model_config = {"from_attributes": True}


class UserSubscriptionOut(BaseModel):
    plan: SubscriptionPlanOut | None = None
    expires_at: datetime | None = None
    is_active: bool = False
    is_cancelled: bool = False


class SubscriptionBuyRequest(BaseModel):
    plan_id: int
