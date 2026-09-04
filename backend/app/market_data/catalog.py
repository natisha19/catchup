"""Curated instrument universe.

This is the authoritative answer to "what does this symbol mean?". Resolution
must NEVER delegate the meaning of a bare symbol to an external provider —
Yahoo will happily return *a* security for any string (e.g. ``SBI`` resolves to
"Western Asset Intermediate Muni", a USD bond fund), which is wrong for CatchUp.

Instead, a human-curated catalog maps the names/symbols users actually type to
the canonical instrument: NSE symbol as the business key, NSE exchange, INR
currency and the Yahoo provider ticker used to fetch market data.

Rules:
  * ``resolve_exact`` / ``search`` consult ONLY this catalog — no network calls.
  * A catalog symbol is authoritative. The provider is asked only for symbols
    the catalog does not know, and only when the user supplied a fully-qualified
    provider ticker (e.g. ``ABCD.US``); bare symbols must exist in the catalog.
"""

from __future__ import annotations

from app.domain.entities import Instrument

# (instrument_id, symbol, company_name, exchange, currency, provider_symbol, sector)
# ``symbol`` is the exchange ticker the frontend shows (NSE symbol for Indian names).
# ``provider_symbol`` is the ticker fetched from the market-data provider.
# instrument_id defaults to ``symbol`` and is the stable business key.
_CATALOG: list[tuple[str, str, str, str, str, str, str | None]] = [
    # ---- NSE large-caps (canonical examples) -------------------------------
    ("SBIN", "SBIN", "State Bank of India", "NSE", "INR", "SBIN.NS", "Financials"),
    ("TCS", "TCS", "Tata Consultancy Services", "NSE", "INR", "TCS.NS", "IT"),
    ("RELIANCE", "RELIANCE", "Reliance Industries", "NSE", "INR", "RELIANCE.NS", "Energy"),
    # ---- Additional widely-watched NSE names -------------------------------
    ("HDFCBANK", "HDFCBANK", "HDFC Bank", "NSE", "INR", "HDFCBANK.NS", "Financials"),
    ("INFY", "INFY", "Infosys", "NSE", "INR", "INFY.NS", "IT"),
    ("ITC", "ITC", "ITC Limited", "NSE", "INR", "ITC.NS", "Consumer Staples"),
    ("BHARTIARTL", "BHARTIARTL", "Bharti Airtel", "NSE", "INR", "BHARTIARTL.NS", "Telecom"),
    ("ICICIBANK", "ICICIBANK", "ICICI Bank", "NSE", "INR", "ICICIBANK.NS", "Financials"),
    ("HINDUNILVR", "HINDUNILVR", "Hindustan Unilever", "NSE", "INR", "HINDUNILVR.NS", "Consumer Staples"),
    ("LT", "LT", "Larsen & Toubro", "NSE", "INR", "LT.NS", "Industrials"),
    ("WIPRO", "WIPRO", "Wipro", "NSE", "INR", "WIPRO.NS", "IT"),
    ("MARUTI", "MARUTI", "Maruti Suzuki India", "NSE", "INR", "MARUTI.NS", "Consumer Discretionary"),
    ("TATAMOTORS", "TATAMOTORS", "Tata Motors", "NSE", "INR", "TATAMOTORS.NS", "Consumer Discretionary"),
    ("AXISBANK", "AXISBANK", "Axis Bank", "NSE", "INR", "AXISBANK.NS", "Financials"),
    ("KOTAKBANK", "KOTAKBANK", "Kotak Mahindra Bank", "NSE", "INR", "KOTAKBANK.NS", "Financials"),
    ("BAJFINANCE", "BAJFINANCE", "Bajaj Finance", "NSE", "INR", "BAJFINANCE.NS", "Financials"),
    ("SUNPHARMA", "SUNPHARMA", "Sun Pharmaceutical Industries", "NSE", "INR", "SUNPHARMA.NS", "Healthcare"),
    ("TITAN", "TITAN", "Titan Company", "NSE", "INR", "TITAN.NS", "Consumer Discretionary"),
    ("ONGC", "ONGC", "Oil and Natural Gas Corporation", "NSE", "INR", "ONGC.NS", "Energy"),
    ("NTPC", "NTPC", "NTPC Limited", "NSE", "INR", "NTPC.NS", "Utilities"),
    ("HCLTECH", "HCLTECH", "HCL Technologies", "NSE", "INR", "HCLTECH.NS", "IT"),
    ("TECHM", "TECHM", "Tech Mahindra", "NSE", "INR", "TECHM.NS", "IT"),
    ("ADANIENT", "ADANIENT", "Adani Enterprises", "NSE", "INR", "ADANIENT.NS", "Industrials"),
    ("ADANIPORTS", "ADANIPORTS", "Adani Ports and Special Economic Zone", "NSE", "INR", "ADANIPORTS.NS", "Industrials"),
    ("ASIANPAINT", "ASIANPAINT", "Asian Paints", "NSE", "INR", "ASIANPAINT.NS", "Consumer Discretionary"),
    ("ULTRACEMCO", "ULTRACEMCO", "UltraTech Cement", "NSE", "INR", "ULTRACEMCO.NS", "Materials"),
    ("NESTLEIND", "NESTLEIND", "Nestlé India", "NSE", "INR", "NESTLEIND.NS", "Consumer Staples"),
    ("POWERGRID", "POWERGRID", "Power Grid Corporation of India", "NSE", "INR", "POWERGRID.NS", "Utilities"),
    ("COALINDIA", "COALINDIA", "Coal India", "NSE", "INR", "COALINDIA.NS", "Energy"),
    ("TATASTEEL", "TATASTEEL", "Tata Steel", "NSE", "INR", "TATASTEEL.NS", "Materials"),
    ("JSWSTEEL", "JSWSTEEL", "JSW Steel", "NSE", "INR", "JSWSTEEL.NS", "Materials"),
    ("GRASIM", "GRASIM", "Grasim Industries", "NSE", "INR", "GRASIM.NS", "Materials"),
    ("HDFCLIFE", "HDFCLIFE", "HDFC Life Insurance", "NSE", "INR", "HDFCLIFE.NS", "Financials"),
    ("SBILIFE", "SBILIFE", "SBI Life Insurance", "NSE", "INR", "SBILIFE.NS", "Financials"),
    ("BRITANNIA", "BRITANNIA", "Britannia Industries", "NSE", "INR", "BRITANNIA.NS", "Consumer Staples"),
    ("DIVISLAB", "DIVISLAB", "Divis Laboratories", "NSE", "INR", "DIVISLAB.NS", "Healthcare"),
    ("DRREDDY", "DRREDDY", "Dr. Reddy's Laboratories", "NSE", "INR", "DRREDDY.NS", "Healthcare"),
    ("CIPLA", "CIPLA", "Cipla", "NSE", "INR", "CIPLA.NS", "Healthcare"),
    ("INDUSINDBK", "INDUSINDBK", "IndusInd Bank", "NSE", "INR", "INDUSINDBK.NS", "Financials"),
    ("DMART", "DMART", "Avenue Supermarts", "NSE", "INR", "DMART.NS", "Consumer Discretionary"),
    # ---- Popular global tickers (for completeness, not the primary focus) ----
    ("AAPL", "AAPL", "Apple", "NASDAQ", "USD", "AAPL", "Technology"),
    ("MSFT", "MSFT", "Microsoft", "NASDAQ", "USD", "MSFT", "Technology"),
    ("GOOGL", "GOOGL", "Alphabet Class A", "NASDAQ", "USD", "GOOGL", "Technology"),
    ("NVDA", "NVDA", "NVIDIA", "NASDAQ", "USD", "NVDA", "Technology"),
    ("AMZN", "AMZN", "Amazon.com", "NASDAQ", "USD", "AMZN", "Consumer Discretionary"),
    ("TSLA", "TSLA", "Tesla", "NASDAQ", "USD", "TSLA", "Consumer Discretionary"),
    ("META", "META", "Meta Platforms", "NASDAQ", "USD", "META", "Communication Services"),
    ("V", "V", "Visa", "NYSE", "USD", "V", "Financials"),
    ("TSM", "TSM", "Taiwan Semiconductor Manufacturing", "NYSE", "USD", "TSM", "Technology"),
]

# User-typed aliases -> canonical instrument_id. These make bare, ambiguous
# inputs unambiguous WITHOUT asking any provider:
#     "SBI"        -> "SBIN"   (State Bank of India, not Yahoo's "SBI" bond fund)
#     "STATE BANK" -> SBIN, etc.
_ALIASES: dict[str, str] = {
    "SBI": "SBIN",
    "STATE BANK": "SBIN",
    "STATEBANK": "SBIN",
    "STATE BANK OF INDIA": "SBIN",
    "TATA CONSULTANCY": "TCS",
    "RELIANCE INDUSTRIES": "RELIANCE",
    "HDFC BANK": "HDFCBANK",
    "INFOSYS": "INFY",
    "BHARTI AIRTEL": "BHARTIARTL",
    "ICICI BANK": "ICICIBANK",
    "HINDUSTAN UNILEVER": "HINDUNILVR",
    "LARSEN TOUBRO": "LT",
    "MARUTI SUZUKI": "MARUTI",
    "TATA MOTORS": "TATAMOTORS",
    "AXIS BANK": "AXISBANK",
    "KOTAK MAHINDRA": "KOTAKBANK",
    "LARSEN & TOUBRO": "LT",
    "SUN PHARMA": "SUNPHARMA",
    "OIL AND NATURAL GAS": "ONGC",
    "HCL TECHNOLOGIES": "HCLTECH",
    "TECH MAHINDRA": "TECHM",
    "ADANI ENTERPRISES": "ADANIENT",
    "ASIAN PAINTS": "ASIANPAINT",
    "ULTRATECH CEMENT": "ULTRACEMCO",
    "NESTLE INDIA": "NESTLEIND",
    "POWER GRID": "POWERGRID",
    "COAL INDIA": "COALINDIA",
    "TATA STEEL": "TATASTEEL",
    "JSW STEEL": "JSWSTEEL",
    "SBI LIFE": "SBILIFE",
    "HDFC LIFE": "HDFCLIFE",
    "BRITANNIA": "BRITANNIA",
    "DR REDDYS": "DRREDDY",
    "DR. REDDYS": "DRREDDY",
    "AVENUE SUPERMARTS": "DMART",
    "AMAZON": "AMZN",
    "MICROSOFT": "MSFT",
    "APPLE": "AAPL",
    "GOOGLE": "GOOGL",
    "FACEBOOK": "META",
    "TESLA": "TSLA",
}

# Exchange tokens the catalog accepts in a provider-style suffix (e.g. SBIN.NSE).
_SUFFIX_EXCHANGES = {
    "NS": "NSE",
    "NSE": "NSE",
    "NASD": "NASDAQ",
    "NASDAQ": "NASDAQ",
    "NYSE": "NYSE",
    "NYQ": "NYSE",
    "US": "NASDAQ",
}


class InstrumentCatalog:
    """Static, curated symbol -> instrument resolver (no network access)."""

    def __init__(self, entries: list[Instrument] | None = None) -> None:
        self._entries: dict[str, Instrument] = {}
        self._by_provider: dict[str, str] = {}
        self._aliases: dict[str, str] = dict(_ALIASES)
        for inst in entries or _instrument_rows():
            self._index(inst)

    def _index(self, inst: Instrument) -> None:
        self._entries[inst.instrument_id.upper()] = inst
        if inst.provider_symbol:
            self._by_provider[inst.provider_symbol.upper()] = inst.instrument_id.upper()

    def resolve_exact(self, symbol: str) -> Instrument | None:
        """Return the canonical instrument for a user-typed symbol, or None.

        Matches (in order): instrument_id, provider symbol, exchange-suffixed
        forms (SBIN, SBIN.NS, SBIN.NSE), and curated aliases (SBI -> SBIN).
        Never contacts a provider.
        """
        s = (symbol or "").strip().upper()
        if not s:
            return None

        # 1. Direct business key / NSE symbol.
        if s in self._entries:
            return self._entries[s]

        # 2. Provider (Yahoo) ticker exactly.
        if s in self._by_provider:
            return self._entries[self._by_provider[s]]

        # 3. Exchange-suffixed forms: SBIN.NS, SBIN.NSE.
        if "." in s:
            base, _, suffix = s.partition(".")
            suffix_upper = suffix.strip().upper()
            if suffix_upper in _SUFFIX_EXCHANGES:
                base_entry = self._entries.get(base)
                if base_entry is not None:
                    return base_entry
                alias_id = self._aliases.get(base)
                if alias_id is not None and alias_id in self._entries:
                    return self._entries[alias_id]

        # 4. Curated alias (SBI -> SBIN, STATE BANK OF INDIA -> SBIN).
        if s in self._aliases:
            alias_id = self._aliases[s]
            if alias_id in self._entries:
                return self._entries[alias_id]

        return None

    def search(self, query: str, limit: int = 20) -> list[Instrument]:
        """Case-insensitive partial search over symbol, name, and provider ticker."""
        q = (query or "").strip().upper()
        if not q:
            return []
        hits: dict[str, Instrument] = {}
        for instrument_id, inst in self._entries.items():
            if (
                q in instrument_id
                or q in inst.company_name.upper()
                or (inst.provider_symbol and q in inst.provider_symbol.upper())
                or (inst.symbol and q in inst.symbol.upper())
            ):
                hits[instrument_id] = inst
        # Aliased names also surface their canonical instrument.
        for alias, instrument_id in self._aliases.items():
            if q in alias and instrument_id not in hits and instrument_id in self._entries:
                hits[instrument_id] = self._entries[instrument_id]
        return [hits[k] for k in sorted(hits)][:limit]


def _instrument_rows() -> list[Instrument]:
    rows: list[Instrument] = []
    for instrument_id, symbol, name, exchange, currency, provider_symbol, sector in _CATALOG:
        rows.append(
            Instrument(
                instrument_id=instrument_id,
                symbol=symbol,
                company_name=name,
                exchange=exchange,
                currency=currency,
                provider_symbol=provider_symbol,
                sector=sector,
            )
        )
    return rows


_catalog_instance: InstrumentCatalog | None = None


def default_catalog() -> InstrumentCatalog:
    """Module-level singleton so wiring creates one catalog and reuses it."""
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = InstrumentCatalog()
    return _catalog_instance


__all__ = ["InstrumentCatalog", "default_catalog"]
