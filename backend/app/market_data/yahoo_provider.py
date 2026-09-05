"""Yahoo Finance adapter.

This is the ONLY module allowed to import yfinance. Every other layer sees the
normalized domain types via the MarketDataProvider port.

Failure strategy (spec §10):
- Retry up to PROVIDER_MAX_RETRIES with exponential backoff (1s/2s/4s).
- Classify failures (network/timeout/empty/invalid).
- Return ProviderResult so upstream decides on last-known-valid fallback.
- Never fabricate values - a failed call yields ok=False.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.domain.entities import CorporateEvent, Instrument
from app.domain.enums import CorporateEventStatus, CorporateEventType, ProviderFailure
from app.market_data.data_types import (
    HistoricalData,
    MarketSnapshotCandidate,
    ProviderResult,
)
from app.market_data.provider import MarketDataProvider
from app.market_data.retry import retry_provider_call

logger = logging.getLogger(__name__)

# Corporate events we can reasonably infer from yfinance's calendar/reference
# endpoints. yfinance's corporate-events surface is limited; we normalize what
# we can and leave the rest as historically persisted state.
_EH_EVENT_MAP = {
    "Earnings Date": CorporateEventType.EARNINGS,
}


class YahooFinanceProvider(MarketDataProvider):
    """yfinance-backed MarketDataProvider implementation."""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def source_name(self) -> str:
        return "yahoo-finance"

    # -- resolve --------------------------------------------------------------
    def resolve_instrument(self, symbol: str) -> ProviderResult[Instrument]:
        import yfinance as yf

        def _fetch() -> Instrument:
            original_symbol = symbol.strip().upper()

            candidates = [original_symbol]

            if "." not in original_symbol:
                candidates.append(f"{original_symbol}.NS")

            for provider_symbol in candidates:
                ticker = yf.Ticker(provider_symbol)
                info = _ticker_info(ticker)

                try:
                    history = ticker.history(
                        period="5d",
                        interval="1d",
                        auto_adjust=False,
                    )

                    if history is not None and not history.empty:
                        code = _instrument_id_for(provider_symbol)

                        return Instrument(
                            instrument_id=code,
                            symbol=code,
                            company_name=_pick(info, "shortName", "longName") or code,
                            exchange=_pick(info, "exchange", "exchangeName") or "YAHOO",
                            currency=_pick(
                                info,
                                "financialCurrency",
                                "currency",
                            ) or "USD",
                            provider_symbol=provider_symbol,
                            sector=info.get("sector"),
                        )

                except Exception:
                    continue

            raise ValueError(
                f"Could not resolve Yahoo Finance symbol: {original_symbol}"
            )

        result = retry_provider_call(
            _fetch,
            max_retries=self._max_retries,
            timeout_seconds=self._timeout_seconds,
            source=self.source_name(),
        )
        return result

    # -- snapshots -----------------------------------------------------------
    def get_snapshot(self, instrument: Instrument) -> ProviderResult[MarketSnapshotCandidate]:
        import yfinance as yf

        ticker = yf.Ticker(_provider_symbol(instrument))

        def _fetch() -> MarketSnapshotCandidate:
            # The minute bar's index is the source observation time.  Do not
            # substitute ``datetime.now`` here: that turns delayed Yahoo data
            # into a falsely LIVE quote.
            bars = ticker.history(period="1d", interval="1m", auto_adjust=False)
            if bars is None or bars.empty:
                raise ValueError("provider returned no intraday quote")
            when, bar = next(reversed(list(bars.iterrows())))
            observed_at = _as_utc(
                when.to_pydatetime() if hasattr(when, "to_pydatetime") else when
            )
            price = _to_float(bar.get("Close"))
            # Current volume is the session's cumulative volume, not the last
            # minute-bar's share. The baseline volume is a daily average, so a
            # comparable numerator is what makes the volume ratio meaningful
            # ("today's run-rate vs a typical full session").
            cumulative_volume = _to_float(bars["Volume"].sum(axis=0)) if "Volume" in bars else None
            info = _ticker_info(ticker)
            # These are session values, rather than the final minute-bar's
            # OHLC.  In particular, session open lets the classifier compare a
            # session return against its daily-return baseline without mixing
            # five-minute and daily intervals.
            session_open = _to_float(bars.iloc[0].get("Open"))
            session_high = _to_float(bars["High"].max()) if "High" in bars else None
            session_low = _to_float(bars["Low"].min()) if "Low" in bars else None
            return MarketSnapshotCandidate(
                observed_at=observed_at,
                price=price,
                open=session_open,
                high=session_high,
                low=session_low,
                close=price,
                volume=cumulative_volume,
                currency=str(_pick(info, "financialCurrency", "currency") or "USD").upper(),
            )

        result = retry_provider_call(
            _fetch,
            max_retries=self._max_retries,
            timeout_seconds=self._timeout_seconds,
            source=self.source_name(),
        )
        if not result.ok:
            return result
        if result.value is None or result.value.price is None:
            return ProviderResult.failed(ProviderFailure.EMPTY, message="provider returned no price")
        return result

    # -- historical -----------------------------------------------------------
    def get_historical_data(
        self,
        instrument: Instrument,
        start: datetime,
        end: datetime,
    ) -> ProviderResult[list[HistoricalData]]:
        import yfinance as yf

        ticker = yf.Ticker(_provider_symbol(instrument))

        def _fetch() -> list[HistoricalData]:
            df = ticker.history(
                start=_fmt(start),
                end=_fmt(end),
                interval="1d",
                auto_adjust=False,
            )
            if df is None or df.empty:
                return []
            rows: list[HistoricalData] = []
            for ts, row in df.iterrows():
                close = _to_float(row.get("Close"))
                volume = _to_float(row.get("Volume"))
                if close is None:
                    continue
                when = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
                rows.append(
                    HistoricalData(
                        observed_at=_as_utc(when),
                        price=close,
                        close=close,
                        volume=volume,
                    )
                )
            return rows

        result = retry_provider_call(
            _fetch,
            max_retries=self._max_retries,
            timeout_seconds=self._timeout_seconds,
            source=self.source_name(),
        )
        if not result.ok:
            return result
        if not result.value:
            return ProviderResult.failed(ProviderFailure.EMPTY, message="no historical rows returned")
        return result

    # -- corporate events -----------------------------------------------------
    def get_corporate_events(
        self,
        instrument: Instrument,
        start: datetime,
        end: datetime,
    ) -> ProviderResult[list[CorporateEvent]]:
        import yfinance as yf

        ticker = yf.Ticker(_provider_symbol(instrument))
        now = datetime.now(timezone.utc)

        def _fetch() -> list[CorporateEvent]:
            events: list[CorporateEvent] = []
            try:
                cal = ticker.get_earnings_dates(limit=6)
                if cal is not None and not cal.empty:
                    for idx, row in cal.iterrows():
                        when = _as_utc(idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx)
                        if when < start or when > end:
                            continue
                        events.append(
                            CorporateEvent(
                                instrument_id=instrument.instrument_id,
                                event_type=CorporateEventType.EARNINGS,
                                event_time=when,
                                description="Earnings",
                                source=self.source_name(),
                                status=(
                                    CorporateEventStatus.CONFIRMED
                                    if when <= now
                                    else CorporateEventStatus.SCHEDULED
                                ),
                            )
                        )
            except Exception:  # noqa: BLE001 - corporate events are best-effort
                logger.debug("corporate-events unavailable for %s", instrument.symbol)
            return events

        return retry_provider_call(
            _fetch,
            max_retries=self._max_retries,
            timeout_seconds=self._timeout_seconds,
            source=self.source_name(),
        )


def _provider_symbol(instrument: Instrument) -> str:
    return instrument.provider_symbol or instrument.symbol


def _ticker_info(ticker) -> dict:
    """Best-effort `info` dict from a yfinance ticker (may throw / be empty)."""
    try:
        info = ticker.info
        if isinstance(info, dict):
            return info
    except Exception:  # noqa: BLE001 - info is best-effort
        pass
    return {}


def _pick(info: dict, *keys: str) -> str | None:
    for key in keys:
        val = info.get(key)
        if val:
            return str(val)
    return None


def _instrument_id_for(symbol: str) -> str:
    """Derive a stable business key from a provider symbol.

    'TCS.NS' -> 'TCS'; 'AAPL' -> 'AAPL'. Keeps the key human-meaningful and
    stable across providers that tag a suffix for the exchange.
    """
    if "." in symbol:
        return symbol.split(".", 1)[0].strip().upper()
    return symbol.strip().upper()



def _last_quote(ticker) -> dict:
    """Best-effort current quote dict from yfinance fast_info."""

    quote: dict = {}
    try:
        info = ticker.fast_info
        quote["open"] = _to_float(getattr(info, "open", None))
        quote["high"] = _to_float(getattr(info, "day_high", None))
        quote["low"] = _to_float(getattr(info, "day_low", None))
        quote["close"] = _to_float(getattr(info, "last_price", None))
        quote["volume"] = _to_float(getattr(info, "last_volume", None))
    except Exception:  # noqa: BLE001
        pass
    return quote


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


__all__ = ["YahooFinanceProvider"]
