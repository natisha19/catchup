"""API contract tests using FastAPI TestClient and in-memory fakes.

Verify the wire contract (camelCase field names, endpoint shapes) matches the
frontend's expectations.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.analytics.thresholds import SignificanceThresholds
from app.api.deps import (
    get_catchup_service,
    get_instrument_service,
    get_user_id,
    get_watchlist_service,
)
from app.application.catchup_service import CatchupService
from app.application.instrument_service import InstrumentService
from app.application.watchlist_service import WatchlistService
from app.infrastructure.database import get_session
from app.main import app
from app.market_data.catalog import default_catalog
from app.relevance.ranking import RuleBasedRelevanceRanker
from tests.fakes import (
    FakeChangeSignalRepo,
    FakeInstrumentRepo,
    FakeMarketSnapshotRepo,
    FakeUserLastSeenRepo,
    FakeWatchlistRepo,
    build_instrument,
)

from .test_catchup import make_signal, make_snapshot
from app.domain.enums import SignificanceTier
from tests.fakes import FakeProvider
from tests.test_instrument_service import ResolveSpyProvider


@pytest.fixture
def resolve_client():
    """Client whose watchlist service can resolve bare symbols via a provider."""
    instruments = FakeInstrumentRepo()  # empty catalog => zero-seed only
    snapshots = FakeMarketSnapshotRepo()
    signals = FakeChangeSignalRepo()
    watchlists = FakeWatchlistRepo(instruments)
    last_seen = FakeUserLastSeenRepo()

    resolver_instrument = build_instrument("TCS", "TCS.NS", "Tata Consultancy Services")
    provider = FakeProvider(resolvable={"TCS.NS": resolver_instrument})
    instrument_service = InstrumentService(instruments, provider=provider)
    watchlist_service = WatchlistService(
        watchlists=watchlists,
        instruments=instruments,
        snapshots=snapshots,
        min_baseline_returns=20,
        resolver=instrument_service.resolve_and_save,
    )
    catchup = CatchupService(
        watchlists=watchlists,
        instruments=instruments,
        snapshots=snapshots,
        signals=signals,
        last_seen=last_seen,
        ranker=RuleBasedRelevanceRanker(),
        min_baseline_returns=20,
        stale_threshold_minutes=30,
    )

    _dummy_session = object()
    app.dependency_overrides[get_user_id] = lambda: "default-user"
    app.dependency_overrides[get_session] = lambda: iter([_dummy_session])
    app.dependency_overrides[get_catchup_service] = lambda: catchup
    app.dependency_overrides[get_instrument_service] = lambda: instrument_service
    app.dependency_overrides[get_watchlist_service] = lambda: watchlist_service

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def catalog_client():
    """Client wired with the curated instrument universe + a resolve spy.

    The spy fails the test if the provider is ever asked to interpret a bare
    or cataloged symbol (the exact class of bug that made SBI -> a USD bond fund).
    """
    instruments = FakeInstrumentRepo()  # empty local catalog => zero-seed only
    snapshots = FakeMarketSnapshotRepo()
    signals = FakeChangeSignalRepo()
    watchlists = FakeWatchlistRepo(instruments)
    last_seen = FakeUserLastSeenRepo()

    provider = ResolveSpyProvider()
    instrument_service = InstrumentService(
        instruments, provider=provider, catalog=default_catalog()
    )
    watchlist_service = WatchlistService(
        watchlists=watchlists,
        instruments=instruments,
        snapshots=snapshots,
        min_baseline_returns=20,
        resolver=instrument_service.resolve_and_save,
    )
    catchup = CatchupService(
        watchlists=watchlists,
        instruments=instruments,
        snapshots=snapshots,
        signals=signals,
        last_seen=last_seen,
        ranker=RuleBasedRelevanceRanker(),
        min_baseline_returns=20,
        stale_threshold_minutes=30,
    )

    _dummy_session = object()
    app.dependency_overrides[get_user_id] = lambda: "default-user"
    app.dependency_overrides[get_session] = lambda: iter([_dummy_session])
    app.dependency_overrides[get_catchup_service] = lambda: catchup
    app.dependency_overrides[get_instrument_service] = lambda: instrument_service
    app.dependency_overrides[get_watchlist_service] = lambda: watchlist_service

    with TestClient(app) as c:
        yield c, provider

    app.dependency_overrides.clear()


class TestCatalogResolution:
    def test_add_sbi_alias_resolves_to_state_bank_of_india(self, catalog_client):
        client, _ = catalog_client
        resp = client.post("/watchlists/me/items", json={"symbol": "SBI"})
        assert resp.status_code == 201
        items = client.get("/watchlists/me").json()["items"]
        assert len(items) == 1
        assert items[0]["instrument"]["instrumentId"] == "SBIN"
        assert items[0]["instrument"]["companyName"] == "State Bank of India"
        assert items[0]["instrument"]["exchange"] == "NSE"

    def test_cataloged_symbol_never_reaches_provider(self, catalog_client):
        client, provider = catalog_client
        client.post("/watchlists/me/items", json={"symbol": "SBI"})
        client.post("/watchlists/me/items", json={"symbol": "TCS.NS"})
        assert provider.resolve_calls == []

    def test_bare_unknown_symbol_returns_404_without_provider(self, catalog_client):
        client, provider = catalog_client
        resp = client.post("/watchlists/me/items", json={"symbol": "ZZZZ"})
        assert resp.status_code == 404
        assert provider.resolve_calls == []

    def test_search_returns_catalog_rows_on_empty_db(self, catalog_client):
        client, _ = catalog_client
        hits = client.get("/instruments/search", params={"q": "state bank"}).json()
        ids = [h["instrument"]["instrumentId"] for h in hits]
        assert "SBIN" in ids
        assert [h["instrument"]["companyName"] for h in hits if h["instrument"]["instrumentId"] == "SBIN"] == [
            "State Bank of India"
        ]


class TestResolveAndAdd:
    def test_add_by_symbol_resolves_and_persists(self, resolve_client):
        resp = resolve_client.post(
            "/watchlists/me/items", json={"symbol": "TCS.NS"}
        )
        assert resp.status_code == 201
        items = resolve_client.get("/watchlists/me").json()["items"]
        assert len(items) == 1
        assert items[0]["instrument"]["instrumentId"] == "TCS"

    def test_resolved_instrument_searchable_after(self, resolve_client):
        resolve_client.post("/watchlists/me/items", json={"symbol": "TCS.NS"})
        hits = resolve_client.get("/instruments/search", params={"q": "tata"}).json()
        assert len(hits) == 1
        assert hits[0]["instrument"]["instrumentId"] == "TCS"

    def test_add_unresolvable_symbol_returns_404(self, resolve_client):
        resp = resolve_client.post(
            "/watchlists/me/items", json={"symbol": "NOTREAL.NS"}
        )
        assert resp.status_code == 404

    def test_duplicate_add_by_symbol_returns_409(self, resolve_client):
        resolve_client.post("/watchlists/me/items", json={"symbol": "TCS.NS"})
        resp = resolve_client.post("/watchlists/me/items", json={"symbol": "TCS.NS"})
        assert resp.status_code == 409


@pytest.fixture
def client():
    instruments = FakeInstrumentRepo()
    instruments.add(build_instrument("TCS", "TCS.NS", "Tata Consultancy Services"))
    instruments.add(build_instrument("INFY", "INFY.NS", "Infosys"))

    snapshots = FakeMarketSnapshotRepo()
    snapshots.save(make_snapshot("TCS", datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0, 1))
    snapshots.save(make_snapshot("TCS", datetime(2024, 1, 2, tzinfo=timezone.utc), 110.0, 2))
    signals = FakeChangeSignalRepo()
    signals.save(make_signal("TCS", datetime(2024, 1, 2, tzinfo=timezone.utc),
                             SignificanceTier.CRITICAL, current_sid=2))

    watchlists = FakeWatchlistRepo(instruments)
    watchlists.add_item("default-user", "TCS")
    last_seen = FakeUserLastSeenRepo()

    catchup = CatchupService(
        watchlists=watchlists,
        instruments=instruments,
        snapshots=snapshots,
        signals=signals,
        last_seen=last_seen,
        ranker=RuleBasedRelevanceRanker(),
        min_baseline_returns=20,
        stale_threshold_minutes=30,
    )
    instrument_service = InstrumentService(instruments)
    watchlist_service = WatchlistService(
        watchlists=watchlists,
        instruments=instruments,
        snapshots=snapshots,
        min_baseline_returns=20,
    )

    _dummy_session = object()

    app.dependency_overrides[get_user_id] = lambda: "default-user"
    app.dependency_overrides[get_session] = lambda: iter([_dummy_session])
    app.dependency_overrides[get_catchup_service] = lambda: catchup
    app.dependency_overrides[get_instrument_service] = lambda: instrument_service
    app.dependency_overrides[get_watchlist_service] = lambda: watchlist_service

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestCatchupApi:
    def test_get_feed_returns_camelcase_contract(self, client):
        resp = client.get("/catchup")
        assert resp.status_code == 200
        body = resp.json()
        assert "lastCheckedAt" in body
        assert "marketStatus" in body
        assert "providerStatus" in body
        assert "unchangedCount" in body
        changes = body["changes"]
        assert len(changes) == 1
        change = changes[0]
        for key in (
            "id", "instrumentId", "symbol", "companyName", "previousPrice",
            "currentPrice", "returnPct", "zScore", "volumeRatio", "eventType",
            "reasonCodes", "eventDescription", "significance", "observedAt",
            "dataStatus",
        ):
            assert key in change
        assert change["significance"] == "CRITICAL"
        assert change["companyName"] == "Tata Consultancy Services"

    def test_get_instrument_change(self, client):
        resp = client.get("/catchup/TCS")
        assert resp.status_code == 200
        body = resp.json()
        assert body["instrument"]["instrumentId"] == "TCS"
        assert "lastCheckedNote" in body
        assert body["latestSignal"] is not None

    def test_get_instrument_change_404_for_unknown(self, client):
        assert client.get("/catchup/UNKNOWN").status_code == 404

    def test_mark_seen_returns_204(self, client):
        resp = client.post("/catchup/mark-seen")
        assert resp.status_code == 204


class TestWatchlistApi:
    def test_get_watchlist_me(self, client):
        resp = client.get("/watchlists/me")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "updatedAt" in body
        assert len(body["items"]) == 1
        assert body["items"][0]["baselineStatus"] in ("READY", "INSUFFICIENT")

    def test_add_item(self, client):
        client.post("/watchlists/me/items", json={"instrument_id": "INFY"})
        items = client.get("/watchlists/me").json()["items"]
        assert len(items) == 2
        instruments = {i["instrument"]["instrumentId"] for i in items}
        assert instruments == {"TCS", "INFY"}

    def test_remove_item(self, client):
        client.delete("/watchlists/me/items/TCS")
        assert client.get("/watchlists/me").json()["items"] == []


class TestInstrumentApi:
    def test_search_returns_instrument_objects(self, client):
        resp = client.get("/instruments/search", params={"q": "info"})
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert body[0]["instrument"]["instrumentId"] == "INFY"


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code in (200, 503)
