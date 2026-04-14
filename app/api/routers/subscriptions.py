from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.user import User
from app.schemas.subscription import (
    PLAN_FEATURES,
    SubscriptionBuyRequest,
    SubscriptionPlanOut,
    UserSubscriptionOut,
)

public_router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
customer_router = APIRouter(
    prefix="/subscriptions",
    tags=["subscriptions"],
    dependencies=[Depends(require_role("customer"))],
)


def _plan_to_out(plan: SubscriptionPlan) -> SubscriptionPlanOut:
    return SubscriptionPlanOut(
        id=plan.id,
        name=plan.name,
        price=float(plan.price),
        duration_days=plan.duration_days,
        features=PLAN_FEATURES.get(plan.name, []),
    )


async def _get_active_subscription(db: AsyncSession, user_id: int) -> Subscription | None:
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user_id, Subscription.is_active.is_(True))
    )
    return result.scalars().first()


@public_router.get("/plans", response_model=list[SubscriptionPlanOut])
async def list_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.id))
    plans = result.scalars().all()
    return [_plan_to_out(p) for p in plans]


@customer_router.get("/my", response_model=UserSubscriptionOut)
async def my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await _get_active_subscription(db, current_user.id)
    if sub is None:
        return UserSubscriptionOut(is_active=False)
    return UserSubscriptionOut(
        plan=_plan_to_out(sub.plan),
        expires_at=sub.expires_at,
        is_active=sub.is_active,
        is_cancelled=sub.is_cancelled,
    )


@customer_router.post("/buy", response_model=UserSubscriptionOut)
async def buy_subscription(
    body: SubscriptionBuyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(SubscriptionPlan, body.plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    now = datetime.now(timezone.utc)
    sub = await _get_active_subscription(db, current_user.id)
    if sub is not None:
        base = sub.expires_at if sub.expires_at > now else now
        sub.expires_at = base + timedelta(days=plan.duration_days)
        sub.is_cancelled = False
        sub.is_active = True
        sub.plan_id = plan.id
    else:
        sub = Subscription(
            user_id=current_user.id,
            plan_id=plan.id,
            expires_at=now + timedelta(days=plan.duration_days),
            is_active=True,
            is_cancelled=False,
        )
        db.add(sub)

    current_user.is_premium = True
    await db.commit()
    await db.refresh(sub, attribute_names=["plan"])

    return UserSubscriptionOut(
        plan=_plan_to_out(sub.plan),
        expires_at=sub.expires_at,
        is_active=sub.is_active,
        is_cancelled=sub.is_cancelled,
    )


@customer_router.post("/cancel", response_model=UserSubscriptionOut)
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await _get_active_subscription(db, current_user.id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active subscription not found")
    sub.is_cancelled = True
    await db.commit()
    await db.refresh(sub, attribute_names=["plan"])
    return UserSubscriptionOut(
        plan=_plan_to_out(sub.plan),
        expires_at=sub.expires_at,
        is_active=sub.is_active,
        is_cancelled=sub.is_cancelled,
    )
