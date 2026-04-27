"""add missing columns and tables

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- restaurants: add missing columns ---
    op.add_column("restaurants", sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("restaurants", sa.Column("preparation_time_min", sa.Integer(), nullable=True))
    op.add_column("restaurants", sa.Column("preparation_time_max", sa.Integer(), nullable=True))

    # --- subscription_features ---
    op.create_table(
        "subscription_features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- subscription_plan_features ---
    op.create_table(
        "subscription_plan_features",
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["feature_id"], ["subscription_features.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("plan_id", "feature_id"),
    )

    # --- menu_categories ---
    op.create_table(
        "menu_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurant_id", "name", name="uq_menu_category_restaurant_name"),
    )

    # --- menu_items: add missing columns ---
    # weight_grams — nullable, safe to add
    op.add_column("menu_items", sa.Column("weight_grams", sa.Integer(), nullable=True))
    # menu_category_id — nullable in migration (existing rows have no category yet)
    op.add_column("menu_items", sa.Column("menu_category_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_menu_items_menu_category_id",
        "menu_items",
        "menu_categories",
        ["menu_category_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_menu_items_menu_category_id", "menu_items", type_="foreignkey")
    op.drop_column("menu_items", "menu_category_id")
    op.drop_column("menu_items", "weight_grams")
    op.drop_table("menu_categories")
    op.drop_table("subscription_plan_features")
    op.drop_table("subscription_features")
    op.drop_column("restaurants", "preparation_time_max")
    op.drop_column("restaurants", "preparation_time_min")
    op.drop_column("restaurants", "review_count")
