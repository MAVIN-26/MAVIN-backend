from datetime import datetime, time, timezone

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.order import OrderRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.admin_stats import AdminStats


class AdminStatsService:
    def __init__(self, db: AsyncSession) -> None:
        self.orders = OrderRepository(db)
        self.subscriptions = SubscriptionRepository(db)

    async def get_stats(self) -> AdminStats:
        now = datetime.now(timezone.utc)
        start_of_day = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

        orders_today = await self.orders.count_created_since(start_of_day)
        revenue_total = await self.orders.sum_revenue_completed()
        active_subs = await self.subscriptions.count_active(now)

        return AdminStats(
            orders_today=orders_today,
            revenue_total=revenue_total,
            active_subscriptions_count=active_subs,
        )


def get_admin_stats_service(db: AsyncSession = Depends(get_db)) -> AdminStatsService:
    return AdminStatsService(db)
