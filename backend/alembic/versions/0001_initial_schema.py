"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects.postgresql import BIGINT

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instrument_id", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("symbol", sa.String(32), nullable=False, index=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("exchange", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("provider_symbol", sa.String(32), nullable=True),
        sa.Column("sector", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False, server_default="My watchlist"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("watchlist_id", sa.Integer(), sa.ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("instrument_id", sa.String(64), sa.ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("watchlist_id", "instrument_id", "removed_at", name="uq_watchlist_item_active"),
    )

    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instrument_id", sa.String(64), sa.ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("data_status", sa.String(16), nullable=False),
        sa.Index("ix_market_snapshots_instrument_observed", "instrument_id", "observed_at"),
        sa.UniqueConstraint("instrument_id", "observed_at", "source", name="uq_market_snapshot_dedup"),
    )

    op.create_table(
        "corporate_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instrument_id", sa.String(64), sa.ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("raw_reference", sa.Text(), nullable=True),
        sa.UniqueConstraint("instrument_id", "event_type", "event_time", name="uq_corporate_event_dedup"),
    )

    op.create_table(
        "change_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instrument_id", sa.String(64), sa.ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("previous_snapshot_id", sa.BigInteger(), nullable=True),
        sa.Column("current_snapshot_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("previous_price", sa.Float(), nullable=True),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("return_pct", sa.Float(), nullable=True),
        sa.Column("baseline_mean", sa.Float(), nullable=True),
        sa.Column("baseline_std", sa.Float(), nullable=True),
        sa.Column("z_score", sa.Float(), nullable=True),
        sa.Column("current_volume", sa.Float(), nullable=True),
        sa.Column("baseline_average_volume", sa.Float(), nullable=True),
        sa.Column("volume_ratio", sa.Float(), nullable=True),
        sa.Column("significance", sa.String(16), nullable=False),
        sa.Column("reason_codes", sa.Text(), nullable=False),
        sa.Column("data_status", sa.String(16), nullable=False),
        sa.Column("event_description", sa.String(255), nullable=True),
        sa.Index("ix_change_signals_instrument_observed", "instrument_id", "observed_at"),
    )

    op.create_table(
        "user_last_seen",
        sa.Column("user_id", sa.String(64), primary_key=True),
        sa.Column("instrument_id", sa.String(64), primary_key=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_snapshot_id", sa.BigInteger(), nullable=True),
        sa.Index("ix_user_last_seen_user_instrument", "user_id", "instrument_id"),
    )


def downgrade() -> None:
    op.drop_table("user_last_seen")
    op.drop_table("change_signals")
    op.drop_table("corporate_events")
    op.drop_table("market_snapshots")
    op.drop_table("watchlist_items")
    op.drop_table("watchlists")
    op.drop_table("instruments")
