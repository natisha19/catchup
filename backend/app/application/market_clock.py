"""Market clock.

Determines marketStatus separately from dataStatus.

Key rule (spec §26, §60): "market closed" is NOT the same as "data unavailable",
and it is NOT the same as "stale provider data". marketStatus answers "is the
exchange currently inside a trading session?" using an NSE-aware calendar —
trading hours 09:15–15:30 IST, Monday–Friday, holiday-aware. It is never inferred
from data recency. Freshness is reported separately through each snapshot's
DataStatus (LIVE/DELAYED/STALE/UNAVAILABLE) and the feed's provider_status.

For v1 the calendar is a deterministic, curated implementation: weekday rules
plus a fixed-date subset of NSE national holidays, all timezone-correct against
Asia/Kolkata. It has no network dependency and can be replaced by a data-driven
annual calendar without touching callers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.domain.enums import MarketStatus

IST = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc

SESSION_START_HOUR = 9
SESSION_START_MINUTE = 15
SESSION_END_HOUR = 15
SESSION_END_MINUTE = 30

# Curated fixed-date NSE holidays (month, day). The exchange publishes an annual
# trading calendar; this deterministic subset captures long-standing national
# holidays. Holiday rules are data here, not control flow.
NSE_HOLIDAYS: frozenset[tuple[int, int]] = frozenset(
    {
        (1, 26),   # Republic Day
        (8, 15),   # Independence Day
        (10, 2),   # Gandhi Jayanti
        (12, 25),  # Christmas
    }
)


def _to_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)


class NseCalendar:
    """Deterministic NSE trading calendar (no network, no data recency)."""

    def is_trading_day(self, dt: datetime) -> bool:
        dt = _to_ist(dt)
        return dt.weekday() < 5 and (dt.month, dt.day) not in NSE_HOLIDAYS

    def is_session_open(self, now: datetime | None = None) -> bool:
        """True only inside a live NSE session (09:15–15:30 IST, trading day)."""
        now = _to_ist(now or datetime.now(IST))
        if not self.is_trading_day(now):
            return False
        start = self._session_start(now)
        end = self._session_end(now)
        return start <= now < end

    def previous_session_end(self, now: datetime | None = None) -> datetime:
        """Close time of the last completed (or currently ongoing) NSE session.

        Returns an IST-aware datetime ready for ISO serialization.
        """
        now = _to_ist(now or datetime.now(IST))
        if not self.is_trading_day(now):
            return self._session_end(self._previous_trading_day(now))
        if now < self._session_start(now):
            return self._session_end(self._previous_trading_day(now))
        # Trading day, at/after session start: the referenced session is the
        # one running (or that just closed) today.
        return self._session_end(now)

    @staticmethod
    def _session_start(day: datetime) -> datetime:
        return day.replace(
            hour=SESSION_START_HOUR,
            minute=SESSION_START_MINUTE,
            second=0,
            microsecond=0,
        )

    @staticmethod
    def _session_end(day: datetime) -> datetime:
        return day.replace(
            hour=SESSION_END_HOUR,
            minute=SESSION_END_MINUTE,
            second=0,
            microsecond=0,
        )

    def _previous_trading_day(self, dt: datetime, max_lookback: int = 30) -> datetime:
        day = dt
        for _ in range(max_lookback):
            day = day - timedelta(days=1)
            if self.is_trading_day(day):
                return day
        # Unreachable in practice for a holiday calendar; keep a valid day.
        return day


def market_status(
    latest_observed_at: datetime | None,
    *,
    now: datetime | None = None,
    calendar: NseCalendar | None = None,
) -> MarketStatus:
    """The exchange-calendar truth about whether the market is open.

    Three and only three states:

    - ``OPEN`` — an NSE session is live right now (regardless of how fresh the
      last observation is; staleness shows up in DataStatus, not marketStatus).
    - ``CLOSED`` — no session is in progress (night, weekend, holiday).
    - ``UNKNOWN`` — there is no observation at all yet, so we cannot even say
      whether data for this watchlist exists.

    ``stale_threshold_minutes`` is intentionally no longer consulted here: a
    closed market is decided by the calendar, never by data recency.
    """
    if latest_observed_at is None:
        return MarketStatus.UNKNOWN
    cal = calendar or NseCalendar()
    if cal.is_session_open(now):
        return MarketStatus.OPEN
    return MarketStatus.CLOSED