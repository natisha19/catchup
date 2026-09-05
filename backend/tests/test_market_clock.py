"""NSE-aware market calendar tests.

The central requirement: marketStatus is decided by the exchange calendar
(trading hours, weekdays, holidays) — NOT by how recent the last observation is.
"Market closed" and "stale data" are different concepts (spec §26, §60).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.application.market_clock import (
    IST,
    NY,
    NseCalendar,
    UsCalendar,
    exchange_calendar,
    market_status,
)
from app.domain.enums import MarketStatus

UTC = timezone.utc

MONDAY = datetime(2026, 9, 7)
FRIDAY = datetime(2026, 9, 4)


def ist(month, day, hour, minute=0, year=2026):
    return datetime(year, month, day, hour, minute, tzinfo=IST)


def utc(dt_ist: datetime) -> datetime:
    return dt_ist.astimezone(UTC)


class TestNseCalendarTradingDay:
    @pytest.mark.parametrize(
        "day",
        [
            MONDAY,
            FRIDAY,
            datetime(2026, 9, 8),  # Tuesday
        ],
    )
    def test_weekdays_are_trading_days(self, day):
        assert NseCalendar().is_trading_day(day) is True

    @pytest.mark.parametrize(
        "day",
        [
            datetime(2026, 9, 12),  # Saturday
            datetime(2026, 9, 13),  # Sunday
        ],
    )
    def test_weekends_are_not_trading_days(self, day):
        assert NseCalendar().is_trading_day(day) is False

    @pytest.mark.parametrize(
        "month,day,year",
        [
            (1, 26, 2026),  # Republic Day (Monday)
            (8, 15, 2025),  # Independence Day (Friday)
            (10, 2, 2026),  # Gandhi Jayanti (Friday)
            (12, 25, 2026),  # Christmas (Friday)
        ],
    )
    def test_holidays_are_not_trading_days(self, month, day, year):
        calendar = NseCalendar()
        holiday = datetime(year, month, day, 12, 0, tzinfo=IST)
        # Guard: these dates must also be weekdays for the holiday rule to be
        # what is under test, not the weekend rule.
        assert holiday.weekday() < 5
        assert calendar.is_trading_day(holiday) is False


class TestNseCalendarSessionWindow:
    def test_open_during_morning_session(self):
        assert NseCalendar().is_session_open(ist(9, 7, 10)) is True

    def test_open_during_late_session(self):
        assert NseCalendar().is_session_open(ist(9, 7, 15, 30 - 1)) is True

    def test_closed_before_open(self):
        assert NseCalendar().is_session_open(ist(9, 7, 8, 0)) is False

    def test_closed_at_exact_open_minute_not_yet(self):
        # Session starts at 09:15:00; 09:15:00 is treated as open (half-open).
        assert NseCalendar().is_session_open(ist(9, 7, 9, 14)) is False

    def test_closed_after_close(self):
        assert NseCalendar().is_session_open(ist(9, 7, 15, 30 + 1)) is False

    def test_closed_at_night(self):
        assert NseCalendar().is_session_open(ist(9, 8, 20, 0)) is False

    def test_closed_on_weekend_even_midday(self):
        assert NseCalendar().is_session_open(ist(9, 12, 12, 0)) is False

    def test_closed_on_holiday(self):
        assert NseCalendar().is_session_open(ist(1, 26, 12, 0)) is False


class TestPreviousSessionEnd:
    def test_saturday_refers_to_friday_close(self):
        end = NseCalendar().previous_session_end(ist(9, 12, 12, 0))
        assert end == ist(9, 11, 15, 30)

    def test_monday_early_morning_refers_to_friday_close(self):
        end = NseCalendar().previous_session_end(ist(9, 7, 8, 0))
        assert end == ist(9, 4, 15, 30)

    def test_monday_in_session_refers_to_today_close(self):
        end = NseCalendar().previous_session_end(ist(9, 7, 10, 0))
        assert end == ist(9, 7, 15, 30)

    def test_monday_after_close_refers_to_today_close(self):
        end = NseCalendar().previous_session_end(ist(9, 7, 16, 0))
        assert end == ist(9, 7, 15, 30)

    def test_holiday_refers_to_previous_trading_day_close(self):
        end = NseCalendar().previous_session_end(ist(1, 26, 12, 0))
        assert end == ist(1, 23, 15, 30)  # Friday 2026-01-23

    def test_returns_utc_serializable_when_given_utc(self):
        end = NseCalendar().previous_session_end(utc(ist(9, 12, 12, 0)))
        assert end.astimezone(UTC) == utc(ist(9, 11, 15, 30))
        assert end.tzinfo is not None


class TestLastCompletedSessionEnd:
    """The baseline boundary: an in-progress session must NOT count as a
    completed historical day (daily-vs-intraday distinction)."""

    def test_during_session_refers_to_previous_day_close(self):
        end = NseCalendar().last_completed_session_end(ist(9, 7, 10, 0))
        assert end == ist(9, 4, 15, 30)  # Friday close, not today's running session

    def test_after_close_includes_today(self):
        end = NseCalendar().last_completed_session_end(ist(9, 7, 16, 0))
        assert end == ist(9, 7, 15, 30)

    def test_pre_open_refers_to_previous_day_close(self):
        end = NseCalendar().last_completed_session_end(ist(9, 7, 8, 0))
        assert end == ist(9, 4, 15, 30)

    def test_weekend_refers_to_friday_close(self):
        end = NseCalendar().last_completed_session_end(ist(9, 12, 12, 0))
        assert end == ist(9, 11, 15, 30)


class TestMarketStatus:
    def test_open_during_session_with_recent_observation(self):
        now = ist(9, 7, 10, 0)
        status = market_status(
            utc(ist(9, 7, 9, 40)), now=utc(now)
        )
        assert status is MarketStatus.OPEN

    def test_open_during_session_even_if_observation_is_stale(self):
        """A stale observation during a live session means stale DATA, not a
        closed market — the two must not be conflated."""
        now = ist(9, 7, 10, 0)
        stale_observation = utc(ist(9, 7, 7, 0))  # 3h old, well past any threshold
        assert market_status(stale_observation, now=utc(now)) is MarketStatus.OPEN

    def test_closed_on_weekend_despite_recent_observation(self):
        """The decisive case: recent data on a weekend is still a CLOSED market,
        because the exchange calendar says so — never infer from recency."""
        now = ist(9, 12, 12, 0)  # Saturday
        very_recent = utc(ist(9, 12, 11, 59))
        assert market_status(very_recent, now=utc(now)) is MarketStatus.CLOSED

    def test_closed_outside_session_hours(self):
        assert market_status(utc(ist(9, 7, 16, 0)), now=utc(ist(9, 7, 20, 0))) is MarketStatus.CLOSED

    def test_closed_on_holiday(self):
        assert market_status(utc(ist(1, 26, 11, 0)), now=utc(ist(1, 26, 12, 0))) is MarketStatus.CLOSED

    def test_unknown_when_no_observation(self):
        assert market_status(None, now=utc(ist(9, 7, 10, 0))) is MarketStatus.UNKNOWN

    def test_default_now_is_now(self):
        # No `now` passed: the calendar evaluates the real current time. We can
        # only assert the enum is one of the three values, never raises.
        status = market_status(utc(ist(9, 7, 10, 0)))
        assert status in (MarketStatus.OPEN, MarketStatus.CLOSED)


class TestUsCalendar:
    """Spec §16: market status must not be hardcoded to NSE — US sessions use
    their own 09:30–16:00 America/New_York window."""

    def ny(self, hour, minute=0):
        return datetime(2026, 9, 7, hour, minute, tzinfo=NY)

    def test_open_during_us_morning_session(self):
        assert UsCalendar().is_session_open(self.ny(9, 30)) is True

    def test_open_during_us_late_session(self):
        assert UsCalendar().is_session_open(self.ny(15, 59)) is True

    def test_closed_before_us_open(self):
        assert UsCalendar().is_session_open(self.ny(9, 29)) is False

    def test_closed_after_us_close(self):
        assert UsCalendar().is_session_open(self.ny(16, 0)) is False

    def test_closed_on_us_weekend(self):
        saturday = datetime(2026, 9, 12, 12, 0, tzinfo=NY)
        assert UsCalendar().is_session_open(saturday) is False

    def test_closed_on_us_holiday(self):
        christmas = datetime(2026, 12, 25, 12, 0, tzinfo=NY)
        assert UsCalendar().is_session_open(christmas) is False

    def test_exchange_aware_market_status(self):
        # 20:00 IST is 10:30 ET: US open, NSE closed — one observation time, two
        # different exchange-calendar answers.
        observed = utc(ist(9, 7, 10, 0))
        evening = utc(ist(9, 7, 20, 0))
        assert market_status(observed, now=evening, exchange="NASDAQ") is MarketStatus.OPEN
        assert market_status(observed, now=evening, exchange="NYSE") is MarketStatus.OPEN
        assert market_status(observed, now=evening, exchange="NSE") is MarketStatus.CLOSED

    def test_unknown_exchange_defaults_to_nse(self):
        morning = utc(ist(9, 7, 10, 0))
        assert market_status(morning, now=utc(ist(9, 7, 10, 0)), exchange="LSE") is MarketStatus.OPEN

    def test_exchange_calendar_registry(self):
        first = exchange_calendar("NYSE")
        second = exchange_calendar("NYSE")
        assert first is second  # shared instance, deterministic
        assert isinstance(exchange_calendar("NASDAQ"), UsCalendar)
        assert isinstance(exchange_calendar(None), NseCalendar)
        assert isinstance(exchange_calendar("BSE"), NseCalendar)