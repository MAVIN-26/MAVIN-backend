from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.subscription import (
    SubscriptionBuyRequest,
    SubscriptionPlanOut,
    UserSubscriptionOut,
)
from app.services.subscription import SubscriptionService, get_subscription_service

public_router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
customer_router = APIRouter(
    prefix="/subscriptions",
    tags=["subscriptions"],
    dependencies=[Depends(require_role("customer"))],
)


@public_router.get("/plans", response_model=list[SubscriptionPlanOut])
async def list_plans(service: SubscriptionService = Depends(get_subscription_service)):
    return await service.list_plans()


@customer_router.get("/my", response_model=UserSubscriptionOut)
async def my_subscription(
    current_user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    sub = await service.get_my(current_user.id)
    if sub is None:
        return UserSubscriptionOut(is_active=False)
    return sub


@customer_router.post("/buy", response_model=UserSubscriptionOut)
async def buy_subscription(
    body: SubscriptionBuyRequest,
    current_user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return await service.buy(current_user, body.plan_id)


@customer_router.post("/cancel", response_model=UserSubscriptionOut)
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return await service.cancel(current_user.id)
