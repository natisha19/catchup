"""Catalog-first resolution: the service must never ask a provider what a bare,
cataloged symbol means; it may only fall back for fully-qualified provider
tickers the catalog does not know.
"""

from __future__ import annotations

import pytest

from app.application.instrument_service import InstrumentNotFoundError, InstrumentService
from app.market_data.catalog import default_catalog
from tests.fakes import FakeInstrumentRepo, FakeProvider, build_instrument


class ResolveSpyProvider(FakeProvider):
    """Fails the test if ``resolve_instrument`` is ever consulted."""

    def __init__(self, resolvable=None):
        super().__init__(resolvable=resolvable or {})
        self.resolve_calls: list[str] = []

    def resolve_instrument(self, symbol: str):
        self.resolve_calls.append(symbol)
        return super().resolve_instrument(symbol)


def test_catalog_alias_resolves_without_provider_call():
    repo = FakeInstrumentRepo()
    provider = ResolveSpyProvider()
    service = InstrumentService(repo, provider=provider, catalog=default_catalog())

    inst = service.resolve_and_save("SBI")

    assert provider.resolve_calls == []
    assert inst.instrument_id == "SBIN"
    assert inst.company_name == "State Bank of India"
    assert repo.get("SBIN").provider_symbol == "SBIN.NS"


def test_catalog_symbol_resolves_without_provider_call():
    repo = FakeInstrumentRepo()
    provider = ResolveSpyProvider()
    service = InstrumentService(repo, provider=provider, catalog=default_catalog())

    inst = service.resolve_and_save("TCS.NS")

    assert provider.resolve_calls == []
    assert inst.instrument_id == "TCS"
    assert repo.get("TCS") is not None


def test_bare_unknown_symbol_rejected_without_provider_call():
    repo = FakeInstrumentRepo()
    provider = ResolveSpyProvider()
    service = InstrumentService(repo, provider=provider, catalog=default_catalog())

    with pytest.raises(InstrumentNotFoundError):
        service.resolve_and_save("ZZZZ")

    assert provider.resolve_calls == []


def test_fully_qualified_unknown_symbol_falls_back_to_provider():
    repo = FakeInstrumentRepo()
    provider = ResolveSpyProvider(
        resolvable={"ABCD.US": build_instrument("ABCD", "ABCD.US", "Alpha Beta Corp", currency="USD")}
    )
    service = InstrumentService(repo, provider=provider, catalog=default_catalog())

    inst = service.resolve_and_save("ABCD.US")

    assert provider.resolve_calls == ["ABCD.US"]
    assert inst.instrument_id == "ABCD"
    assert repo.get("ABCD") is not None


def test_fully_qualified_unknown_unresolvable_raises():
    repo = FakeInstrumentRepo()
    provider = ResolveSpyProvider()  # empty resolvable map
    service = InstrumentService(repo, provider=provider, catalog=default_catalog())

    with pytest.raises(InstrumentNotFoundError):
        service.resolve_and_save("NOPE.US")
    assert provider.resolve_calls == ["NOPE.US"]


def test_without_catalog_provider_fallback_preserved():
    """Existing zero-seed flow (no catalog wired) keeps working for qualified tickers."""
    repo = FakeInstrumentRepo()
    provider = ResolveSpyProvider(
        resolvable={"TCS.NS": build_instrument("TCS", "TCS.NS", "Tata Consultancy Services")}
    )
    service = InstrumentService(repo, provider=provider)

    inst = service.resolve_and_save("TCS.NS")

    assert provider.resolve_calls == ["TCS.NS"]
    assert inst.instrument_id == "TCS"


def test_resolve_rejects_empty_symbol():
    service = InstrumentService(FakeInstrumentRepo(), catalog=default_catalog())
    with pytest.raises(InstrumentNotFoundError):
        service.resolve_and_save("   ")


def test_search_merges_catalog_and_repo_deduplicated():
    repo = FakeInstrumentRepo()
    repo.add(build_instrument("TCS", "TCS.NS", "Tata Consultancy Services"))
    service = InstrumentService(repo, catalog=default_catalog())

    hits = service.search("tata", limit=20)
    ids = [h.instrument_id for h in hits]

    assert ids.count("TCS") == 1  # catalog copy and repo copy collapse to one
    assert "TATAMOTORS" in ids


def test_get_unknown_raises():
    service = InstrumentService(FakeInstrumentRepo(), catalog=default_catalog())
    with pytest.raises(InstrumentNotFoundError):
        service.get("ZZZZ")