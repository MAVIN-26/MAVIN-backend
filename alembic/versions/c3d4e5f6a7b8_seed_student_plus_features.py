"""seed student plus features

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-15 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FEATURES = [
    "Доступ к ИИ-нутрициологу",
    "Скидка 5% на все заказы",
    "Приоритетная готовка",
]
PLAN_NAME = "Студент+"


def upgrade() -> None:
    conn = op.get_bind()
    plan_id = conn.execute(
        sa.text("SELECT id FROM subscription_plans WHERE name = :n"),
        {"n": PLAN_NAME},
    ).scalar()
    if plan_id is None:
        return

    for sort_order, title in enumerate(FEATURES):
        feature_id = conn.execute(
            sa.text(
                "INSERT INTO subscription_features (title, sort_order, is_active) "
                "VALUES (:t, :s, TRUE) RETURNING id"
            ),
            {"t": title, "s": sort_order},
        ).scalar()
        conn.execute(
            sa.text(
                "INSERT INTO subscription_plan_features (plan_id, feature_id) "
                "VALUES (:p, :f)"
            ),
            {"p": plan_id, "f": feature_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM subscription_features WHERE title = ANY(:titles)"
        ),
        {"titles": FEATURES},
    )
