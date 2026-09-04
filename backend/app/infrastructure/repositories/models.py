"""SQLAlchemy ORM models.

Concrete persistence mapping. These live ONLY in infrastructure and are never
passed up to application/domain layers — services map to/from domain dataclasses
through repositories.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class InstrumentModel(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    provider_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WatchlistModel(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="My watchlist")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WatchlistItemModel(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watchlist_id: Mapped[int] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # A watchlist holds an instrument at most once while active. We cannot
        # use a plain UNIQUE(watchlist_id, instrument_id, removed_at): Postgres
        # treats NULLs as distinct, so multiple active rows (removed_at IS NULL)
        # would slip through. A partial unique index over active rows only is the
        # correct way to express the invariant.
        Index(
            "uq_watchlist_item_active",
            "watchlist_id",
            "instrument_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
    )


class MarketSnapshotModel(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    open: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    data_status: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        Index("ix_market_snapshots_instrument_observed", "instrument_id", "observed_at"),
        # Idempotency: repeated ingestion of the same observation must not
        # create duplicates (instrument + observed_at + source).
        UniqueConstraint(
            "instrument_id", "observed_at", "source", name="uq_market_snapshot_dedup"
        ),
    )


class CorporateEventModel(Base):
    __tablename__ = "corporate_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    raw_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "event_type", "event_time", name="uq_corporate_event_dedup"
        ),
    )


class ChangeSignalModel(Base):
    __tablename__ = "change_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False, index=True
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    previous_snapshot_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_snapshot_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_std: Mapped[float | None] = mapped_column(Float, nullable=True)
    z_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_average_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    significance: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_codes: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    data_status: Mapped[str] = mapped_column(String(16), nullable=False)
    event_description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_change_signals_instrument_observed", "instrument_id", "observed_at"),
        UniqueConstraint(
            "instrument_id", "observed_at", name="uq_change_signal_dedup"
        ),
    )


class UserLastSeenModel(Base):
    __tablename__ = "user_last_seen"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_snapshot_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    __table_args__ = (
        Index("ix_user_last_seen_user_instrument", "user_id", "instrument_id"),
    )
