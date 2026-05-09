"""add restaurant card_bg fields

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-05-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "restaurants",
        sa.Column("card_bg_color", sa.String(length=9), nullable=True),
    )
    op.add_column(
        "restaurants",
        sa.Column("card_bg_image_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("restaurants", "card_bg_image_url")
    op.drop_column("restaurants", "card_bg_color")
