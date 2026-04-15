from datetime import datetime

from pydantic import BaseModel, field_validator


class SubscriptionPlanOut(BaseModel):
    id: int
    name: str
    price: float
    duration_days: int
    features: list[str] = []

    model_config = {"from_attributes": True}

    @field_validator("features", mode="before")
    @classmethod
    def _extract_feature_titles(cls, value):
        if not value:
            return []
        first = value[0] if hasattr(value, "__getitem__") else None
        if first is not None and hasattr(first, "title"):
            return [f.title for f in value if getattr(f, "is_active", True)]
        return value


class UserSubscriptionOut(BaseModel):
    plan: SubscriptionPlanOut | None = None
    expires_at: datetime | None = None
    is_active: bool = False
    is_cancelled: bool = False

    model_config = {"from_attributes": True}


class SubscriptionBuyRequest(BaseModel):
    plan_id: int
