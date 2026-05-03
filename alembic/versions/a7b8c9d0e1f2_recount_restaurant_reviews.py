"""recount restaurant review_count and average_rating from reviews

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill restaurants.review_count and average_rating from reviews table."""
    op.execute(
        """
        UPDATE restaurants r
        SET
            review_count = COALESCE(s.cnt, 0),
            average_rating = COALESCE(s.avg_rating, 0.0)
        FROM (
            SELECT restaurant_id,
                   COUNT(*) AS cnt,
                   AVG(rating)::float AS avg_rating
            FROM reviews
            GROUP BY restaurant_id
        ) s
        WHERE r.id = s.restaurant_id
        """
    )


def downgrade() -> None:
    """No-op: recount is idempotent; we don't restore previous stale values."""
    pass
