"""Market clock.

Determines marketStatus separately from dataStatus.

Key rule (spec §26, §60): "market closed" is NOT the same as "data unavailable",
and it is NOT the same as "stale provider data". marketStatus answers "is the
exchange currently inside a trading session?" using an exchange-aware calendar —
trading hours, weekdays and holidays. It is never inferred from data recency.
Freshness is reported separately through each snapshot's DataStatus
(LIVE/DELAYED/STALE/UNAVAILABLE) and the feed's provider_status.

The calendar is a deterministic, curated implementation: weekday rules plus a
fixed-date subset of holidays, all timezone-correct against the exchange's own
zone. It has no network dependency and can be replaced by a data-driven annual
calendar without touching callers.

Exchanges understood (spec §16: not hardcoded to NSE alone):
  * NSE     — 09:15–15:30 Asia/Kolkata, Mon–Fri + curated national holidays.
  * NASDAQ  — 09:30–16:00 America/New_York, Mon–Fri + curated US holidays.
  * NYSE    — same hours as NASDAQ (both US sessions).
Unknown exchanges default to the NSE calendar so legacy call sites and
instruments without an explicit exchange keep working.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.domain.enums import MarketStatus

IST = ZoneInfo("Asia/Kolkata")
NY = ZoneInfo("America/New_York")
UTC = timezone.utc

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

# Curated fixed-date US holidays shared by NASDAQ and NYSE. Floating holidays
# (e.g. Thanksgiving) are intentionally omitted from this deterministic subset;
# as with NSE, an annual data-driven calendar can replace these later.
US_HOLIDAYS: frozenset[tuple[int, int]] = frozenset(
    {
        (1, 1),    # New Year's Day
        (7, 4),    # Independence Day
        (12, 25),  # Christmas
    }
)

# Canonical exchange names used by the instrument catalog.
NSE = "NSE"
NASDAQ = "NASDAQ"
NYSE = "NYSE"


class TradingCalendar:
    """Deterministic exchange trading calendar (no network, no data recency)."""

    def __init__(
        self,
        *,
        tz,
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int,
        holidays: frozenset[tuple[int, int]],
    ) -> None:
        self._tz = tz
        self._start_hour = start_hour
        self._start_minute = start_minute
        self._end_hour = end_hour
        self._end_minute = end_minute
        self._holidays = holidays

    def _to_local(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(self._tz)

    def is_trading_day(self, dt: datetime) -> bool:
        dt = self._to_local(dt)
        return dt.weekday() < 5 and (dt.month, dt.day) not in self._holidays

    def is_session_open(self, now: datetime | None = None) -> bool:
        """True only inside a live trading session on a trading day."""
        now = self._to_local(now or datetime.now(self._tz))
        if not self.is_trading_day(now):
            return False
        start = self._session_start(now)
        end = self._session_end(now)
        return start <= now < end

    def previous_session_end(self, now: datetime | None = None) -> datetime:
        """Close time of the last completed (or currently ongoing) session.

        Returns a local-tz-aware datetime ready for ISO serialization.
        """
        now = self._to_local(now or datetime.now(self._tz))
        if not self.is_trading_day(now):
            return self._session_end(self._previous_trading_day(now))
        if now < self._session_start(now):
            return self._session_end(self._previous_trading_day(now))
        # Trading day, at/after session start: the referenced session is the
        # one running (or that just closed) today.
        return self._session_end(now)

    def last_completed_session_end(self, now: datetime | None = None) -> datetime:
        """End of the most recent session that has actually finished.

        Unlike :meth:`previous_session_end`, an in-progress session is treated
        as incomplete: while the market is open the boundary rolls back to the
        previous trading day's close. Used to keep partial current-day bars out
        of historical baselines. Returns a local-tz-aware datetime.
        """
        now = self._to_local(now or datetime.now(self._tz))
        if not self.is_trading_day(now):
            return self._session_end(self._previous_trading_day(now))
        start = self._session_start(now)
        end = self._session_end(now)
        if now < start:
            return self._session_end(self._previous_trading_day(now))
        if now < end:
            # Session in progress: no completed bar exists for today yet.
            return self._session_end(self._previous_trading_day(now))
        return end

    def _session_start(self, day: datetime) -> datetime:
        return day.replace(
            hour=self._start_hour,
            minute=self._start_minute,
            second=0,
            microsecond=0,
        )

    def _session_end(self, day: datetime) -> datetime:
        return day.replace(
            hour=self._end_hour,
            minute=self._end_minute,
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


class NseCalendar(TradingCalendar):
    """NSE trading calendar (09:15–15:30 IST, Mon–Fri, NSE holidays)."""

    def __init__(self) -> None:
        super().__init__(
            tz=IST,
            start_hour=9,
            start_minute=15,
            end_hour=15,
            end_minute=30,
            holidays=NSE_HOLIDAYS,
        )


class UsCalendar(TradingCalendar):
    """Shared NASDAQ/NYSE session (09:30–16:00 America/New_York, US holidays)."""

    def __init__(self) -> None:
        super().__init__(
            tz=NY,
            start_hour=9,
            start_minute=30,
            end_hour=16,
            end_minute=0,
            holidays=US_HOLIDAYS,
        )


_EXCHANGE_CALENDARS: dict[str, TradingCalendar] = {
    NSE: NseCalendar(),
    NASDAQ: UsCalendar(),
    NYSE: UsCalendar(),
}


def exchange_calendar(exchange: str | None) -> TradingCalendar:
    """The trading calendar for ``exchange``, defaulting to NSE when unknown."""
    key = (exchange or "").strip().upper()
    return _EXCHANGE_CALENDARS.get(key, _EXCHANGE_CALENDARS[NSE])


def market_status(
    latest_observed_at: datetime | None,
    *,
    now: datetime | None = None,
    calendar: TradingCalendar | None = None,
    exchange: str | None = None,
) -> MarketStatus:
    """The exchange-calendar truth about whether the market is open.

    Three and only three states:

    - ``OPEN`` — a session is live right now on ``exchange`` (regardless of how
      fresh the last observation is; staleness shows up in DataStatus, not
      marketStatus).
    - ``CLOSED`` — no session is in progress (night, weekend, holiday).
    - ``UNKNOWN`` — there is no observation at all yet, so we cannot even say
      whether data for this instrument exists.

    ``exchange`` selects the calendar (NSE/NASDAQ/NYSE); an explicit
    ``calendar`` overrides it for custom callers.
    """
    if latest_observed_at is None:
        return MarketStatus.UNKNOWN
    cal = calendar or exchange_calendar(exchange)
    if cal.is_session_open(now):
        return MarketStatus.OPEN
    return MarketStatus.CLOSED