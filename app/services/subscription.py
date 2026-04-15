from datetime import datetime, timedelta, timezone
from typing import Sequence

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.user import User
from app.repositories.subscription import SubscriptionPlanRepository, SubscriptionRepository


class SubscriptionService:
    def __init__(self, db: AsyncSession) -> None:
        self.plans = SubscriptionPlanRepository(db)
        self.subscriptions = SubscriptionRepository(db)

    async def list_plans(self) -> Sequence[SubscriptionPlan]:
        return await self.plans.list_with_features()

    async def get_my(self, user_id: int) -> Subscription | None:
        return await self.subscriptions.get_active_for_user(user_id)

    async def buy(self, user: User, plan_id: int) -> Subscription:
        plan = await self.plans.get_by_id(plan_id)
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found",
            )

        now = datetime.now(timezone.utc)
        sub = await self.subscriptions.get_active_for_user(user.id)
        if sub is not None:
            base = sub.expires_at if sub.expires_at > now else now
            sub.expires_at = base + timedelta(days=plan.duration_days)
            sub.is_cancelled = False
            sub.is_active = True
            sub.plan_id = plan.id
        else:
            sub = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                expires_at=now + timedelta(days=plan.duration_days),
                is_active=True,
                is_cancelled=False,
            )
            self.subscriptions.add(sub)

        user.is_premium = True
        await self.subscriptions.commit()

        refreshed = await self.subscriptions.get_active_for_user(user.id)
        assert refreshed is not None
        return refreshed

    async def cancel(self, user_id: int) -> Subscription:
        sub = await self.subscriptions.get_active_for_user(user_id)
        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active subscription not found",
            )
        sub.is_cancelled = True
        await self.subscriptions.commit()

        refreshed = await self.subscriptions.get_active_for_user(user_id)
        assert refreshed is not None
        return refreshed


def get_subscription_service(db: AsyncSession = Depends(get_db)) -> SubscriptionService:
    return SubscriptionService(db)
