from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

restaurant_categories = Table(
    "restaurant_categories",
    Base.metadata,
    Column("restaurant_id", Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    pickup_address: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    average_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    preparation_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preparation_time_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    restaurant_admin_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    restaurant_admin: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="restaurant"
    )
    categories: Mapped[list["Category"]] = relationship(  # noqa: F821
        "Category", secondary=restaurant_categories, back_populates="restaurants"
    )
    menu_items: Mapped[list["MenuItem"]] = relationship(  # noqa: F821
        "MenuItem", back_populates="restaurant", cascade="all, delete-orphan"
    )
    menu_categories: Mapped[list["MenuCategory"]] = relationship(  # noqa: F821
        "MenuCategory",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        order_by="MenuCategory.sort_order",
    )
