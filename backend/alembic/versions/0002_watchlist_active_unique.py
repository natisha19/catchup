"""watchlist active-row partial unique index

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-04 00:00:00

The original UNIQUE(watchlist_id, instrument_id, removed_at) did not actually
prevent duplicate active rows: Postgres treats NULLs as distinct, so multiple
active rows (removed_at IS NULL) were allowed. Replace it with a partial unique
index over active rows only.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_OLD_CONSTRAINT = "uq_watchlist_item_active"
_NEW_INDEX = "uq_watchlist_item_active"


def upgrade() -> None:
    # Drop the constraint that silently allowed duplicate active rows.
    op.drop_constraint(_OLD_CONSTRAINT, "watchlist_items", type_="unique")
    # Active rows are unique per (watchlist, instrument); soft-deleted rows
    # (removed_at IS NOT NULL) may repeat freely.
    op.create_index(
        _NEW_INDEX,
        "watchlist_items",
        ["watchlist_id", "instrument_id"],
        unique=True,
        postgresql_where=sa.text("removed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(_NEW_INDEX, table_name="watchlist_items")
    op.create_unique_constraint(
        _OLD_CONSTRAINT, "watchlist_items", ["watchlist_id", "instrument_id", "removed_at"]
    )
