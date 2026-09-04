"""Curated instrument-universe catalog tests.

Regression focus: a bare symbol like ``SBI`` must resolve to State Bank of
India (SBIN) and NOT be handed to an external provider for interpretation.
"""

from __future__ import annotations

import pytest

from app.market_data.catalog import InstrumentCatalog

CASES_TO_CHECK = {
    "SBIN": ("SBIN", "State Bank of India", "NSE", "SBIN.NS"),
    "TCS": ("TCS", "Tata Consultancy Services", "NSE", "TCS.NS"),
    "RELIANCE": ("RELIANCE", "Reliance Industries", "NSE", "RELIANCE.NS"),
    "INFY": ("INFY", "Infosys", "NSE", "INFY.NS"),
    "AAPL": ("AAPL", "Apple", "NASDAQ", "AAPL"),
}


def resolve(symbol: str):
    return InstrumentCatalog().resolve_exact(symbol)


@pytest.mark.parametrize(
    "symbol,expected",
    [
        ("SBI", "SBIN"),
        ("STATE BANK", "SBIN"),
        ("STATE BANK OF INDIA", "SBIN"),
        ("TATA CONSULTANCY", "TCS"),
        ("RELIANCE INDUSTRIES", "RELIANCE"),
        ("INFOSYS", "INFY"),
    ],
)
def test_alias_resolves_to_canonical_instrument(symbol, expected):
    inst = resolve(symbol)
    assert inst is not None
    assert inst.instrument_id == expected
    assert inst.exchange == "NSE"


@pytest.mark.parametrize("symbol", list(CASES_TO_CHECK))
def test_bare_symbol_resolves_to_own_instrument(symbol):
    expected_id, expected_name, expected_exchange, expected_provider = CASES_TO_CHECK[symbol]
    inst = resolve(symbol)
    assert inst is not None
    assert inst.instrument_id == expected_id
    assert inst.company_name == expected_name
    assert inst.exchange == expected_exchange
    assert inst.provider_symbol == expected_provider


@pytest.mark.parametrize(
    "symbol,expected_id",
    [
        ("SBIN.NS", "SBIN"),
        ("SBIN.NSE", "SBIN"),
        ("TCS.NS", "TCS"),
        ("TCS.NSE", "TCS"),
        ("RELIANCE.NS", "RELIANCE"),
    ],
)
def test_exchange_suffixed_symbol_resolves(symbol, expected_id):
    inst = resolve(symbol)
    assert inst is not None
    assert inst.instrument_id == expected_id


@pytest.mark.parametrize(
    "symbol,expected_id",
    [
        ("sbi", "SBIN"),
        ("Tcs", "TCS"),
        ("state bank of india", "SBIN"),
        ("tcs.ns", "TCS"),
    ],
)
def test_resolution_is_case_insensitive(symbol, expected_id):
    assert resolve(symbol).instrument_id == expected_id


@pytest.mark.parametrize("symbol", ["", "ZZZZ", "NOTREAL", "SBIN.XX"])
def test_unknown_or_unsupported_suffix_returns_none(symbol):
    assert resolve(symbol) is None


@pytest.mark.parametrize(
    "query,expected_subset",
    [
        ("bank", {"HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK"}),
        ("state bank", {"SBIN"}),
        ("tata", {"TCS", "TATAMOTORS", "TATASTEEL"}),
        ("sbin", {"SBIN"}),
    ],
)
def test_search_finds_by_name_and_symbol(query, expected_subset):
    hits = InstrumentCatalog().search(query)
    ids = {h.instrument_id for h in hits}
    assert expected_subset.issubset(ids)


def test_search_finds_by_provider_symbol():
    ids = {h.instrument_id for h in InstrumentCatalog().search("tcs.ns")}
    assert ids == {"TCS"}


def test_search_empty_query_returns_empty():
    assert InstrumentCatalog().search("") == []
    assert InstrumentCatalog().search("   ") == []


def test_search_respects_limit():
    hits = InstrumentCatalog().search("bank", limit=2)
    assert len(hits) == 2


def test_search_is_case_insensitive():
    assert {h.instrument_id for h in InstrumentCatalog().search("statebank")} == {"SBIN"}


def test_search_sbi_surfaces_state_bank_of_india():
    ids = {h.instrument_id for h in InstrumentCatalog().search("SBI")}
    assert "SBIN" in ids
    assert "SBILIFE" in ids  # SBI Life legitimately matches too