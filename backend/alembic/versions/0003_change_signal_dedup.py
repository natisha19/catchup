"""enforce change-signal idempotency in the database

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-04 00:00:00
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_change_signal_dedup",
        "change_signals",
        ["instrument_id", "observed_at"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_change_signal_dedup", "change_signals", type_="unique")
