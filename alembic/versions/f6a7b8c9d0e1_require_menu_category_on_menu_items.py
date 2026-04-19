"""require menu_category on menu_items (NOT NULL + FK RESTRICT)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-19 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Tighten menu_items.menu_category_id: NOT NULL, ON DELETE RESTRICT.

    Fails if any menu item currently has menu_category_id IS NULL — those
    rows must be reassigned to an existing category before running.
    """
    op.drop_constraint(
        "fk_menu_items_menu_category_id", "menu_items", type_="foreignkey"
    )
    op.alter_column(
        "menu_items",
        "menu_category_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_menu_items_menu_category_id",
        "menu_items",
        "menu_categories",
        ["menu_category_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_menu_items_menu_category_id", "menu_items", type_="foreignkey"
    )
    op.alter_column(
        "menu_items",
        "menu_category_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_menu_items_menu_category_id",
        "menu_items",
        "menu_categories",
        ["menu_category_id"],
        ["id"],
        ondelete="SET NULL",
    )
