"""seed student plus plan

Revision ID: a1b2c3d4e5f6
Revises: fceec55306b9
Create Date: 2026-04-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "fceec55306b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO subscription_plans (name, price, duration_days) "
            "VALUES ('Студент+', 199, 30)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM subscription_plans WHERE name = 'Студент+'"))
