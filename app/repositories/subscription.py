from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.subscription import Subscription, SubscriptionPlan
from app.repositories.base import BaseRepository


class SubscriptionPlanRepository(BaseRepository[SubscriptionPlan]):
    model = SubscriptionPlan

    async def list_with_features(self) -> Sequence[SubscriptionPlan]:
        result = await self.db.execute(
            select(SubscriptionPlan)
            .options(selectinload(SubscriptionPlan.features))
            .order_by(SubscriptionPlan.id)
        )
        return result.scalars().all()


class SubscriptionRepository(BaseRepository[Subscription]):
    model = Subscription

    async def get_active_for_user(self, user_id: int) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan).selectinload(SubscriptionPlan.features))
            .where(Subscription.user_id == user_id, Subscription.is_active.is_(True))
        )
        return result.scalars().first()
