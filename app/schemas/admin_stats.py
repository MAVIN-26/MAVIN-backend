from pydantic import BaseModel


class AdminStats(BaseModel):
    orders_today: int
    revenue_total: float
    active_subscriptions_count: int
