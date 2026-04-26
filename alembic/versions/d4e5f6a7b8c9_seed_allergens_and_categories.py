"""seed allergens and categories

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ALLERGENS = [
    "Глютен",
    "Молоко",
    "Яйца",
    "Орехи",
    "Соя",
    "Рыба",
    "Моллюски",
    "Кунжут",
]

CATEGORIES = [
    "Бургеры",
    "Суши",
    "Пицца",
    "Здоровая еда",
    "Десерты",
    "Напитки",
]


def upgrade() -> None:
    for name in ALLERGENS:
        op.execute(
            sa.text(
                "INSERT INTO allergens (name) VALUES (:name) "
                "ON CONFLICT (name) DO NOTHING"
            ).bindparams(name=name)
        )

    for name in CATEGORIES:
        op.execute(
            sa.text(
                "INSERT INTO categories (name) VALUES (:name) "
                "ON CONFLICT (name) DO NOTHING"
            ).bindparams(name=name)
        )


def downgrade() -> None:
    for name in CATEGORIES:
        op.execute(
            sa.text("DELETE FROM categories WHERE name = :name").bindparams(name=name)
        )
    for name in ALLERGENS:
        op.execute(
            sa.text("DELETE FROM allergens WHERE name = :name").bindparams(name=name)
        )
