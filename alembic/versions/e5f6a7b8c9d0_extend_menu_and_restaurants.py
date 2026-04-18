"""extend menu and restaurants: menu_categories, weight_grams, preparation_time, review_count

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-18 22:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # menu_categories table
    op.create_table(
        "menu_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "restaurant_id", "name", name="uq_menu_category_restaurant_name"
        ),
    )

    # restaurants: review_count, preparation_time_min/max
    op.add_column(
        "restaurants",
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "restaurants",
        sa.Column("preparation_time_min", sa.Integer(), nullable=True),
    )
    op.add_column(
        "restaurants",
        sa.Column("preparation_time_max", sa.Integer(), nullable=True),
    )

    # menu_items: weight_grams, menu_category_id
    op.add_column(
        "menu_items",
        sa.Column("weight_grams", sa.Integer(), nullable=True),
    )
    op.add_column(
        "menu_items",
        sa.Column("menu_category_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_menu_items_menu_category_id",
        "menu_items",
        "menu_categories",
        ["menu_category_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_menu_items_menu_category_id", "menu_items", type_="foreignkey")
    op.drop_column("menu_items", "menu_category_id")
    op.drop_column("menu_items", "weight_grams")

    op.drop_column("restaurants", "preparation_time_max")
    op.drop_column("restaurants", "preparation_time_min")
    op.drop_column("restaurants", "review_count")

    op.drop_table("menu_categories")
