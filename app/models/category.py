from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    restaurants: Mapped[list["Restaurant"]] = relationship(  # noqa: F821
        "Restaurant", secondary="restaurant_categories", back_populates="categories"
    )
