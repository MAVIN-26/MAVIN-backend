from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


subscription_plan_features = Table(
    "subscription_plan_features",
    Base.metadata,
    Column(
        "plan_id",
        Integer,
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "feature_id",
        Integer,
        ForeignKey("subscription_features.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class SubscriptionFeature(Base):
    __tablename__ = "subscription_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)

    features: Mapped[list["SubscriptionFeature"]] = relationship(
        "SubscriptionFeature",
        secondary=subscription_plan_features,
        order_by="SubscriptionFeature.sort_order",
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan: Mapped["SubscriptionPlan"] = relationship("SubscriptionPlan")
