"""Signed-session identity: token signing + auth endpoints.

The API is built around a single default user, so unauthenticated requests fall
back to DEFAULT_USER_ID unless AUTH_REQUIRED is on. A Bearer token minted by
POST /auth/session makes the request act as that signed identity instead.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    DEFAULT_USER_ID,
    get_catchup_service,
    get_instrument_service,
    get_watchlist_service,
)
from app.api.security import sign_session, token_expiry, verify_session
from app.application.catchup_service import CatchupService
from app.application.instrument_service import InstrumentService
from app.application.watchlist_service import WatchlistService
from app.infrastructure.database import get_session
from app.main import app
from app.relevance.ranking import RuleBasedRelevanceRanker
from tests.fakes import (
    FakeChangeSignalRepo,
    FakeInstrumentRepo,
    FakeMarketSnapshotRepo,
    FakeUserLastSeenRepo,
    FakeWatchlistRepo,
    build_instrument,
)


@pytest.fixture
def auth_client():
    """Client that runs the REAL get_user_id (token/header based) with fakes for
    everything else."""
    instruments = FakeInstrumentRepo()
    instruments.add(build_instrument("TCS", "TCS.NS", "Tata Consultancy Services"))
    snapshots = FakeMarketSnapshotRepo()
    watchlists = FakeWatchlistRepo(instruments)
    catchup = CatchupService(
        watchlists=watchlists,
        instruments=instruments,
        snapshots=snapshots,
        signals=FakeChangeSignalRepo(),
        last_seen=FakeUserLastSeenRepo(),
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
    app.dependency_overrides[get_session] = lambda: iter([_dummy_session])
    app.dependency_overrides[get_catchup_service] = lambda: catchup
    app.dependency_overrides[get_instrument_service] = lambda: instrument_service
    app.dependency_overrides[get_watchlist_service] = lambda: watchlist_service

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestSessionTokens:
    def test_roundtrip(self):
        token = sign_session("alice")
        assert verify_session(token) == "alice"
        assert token_expiry(token) is not None

    def test_different_users_get_distinct_tokens(self):
        assert sign_session("alice") != sign_session("bob")

    def test_malformed_token_rejected(self):
        assert verify_session("") is None
        assert verify_session("garbage") is None
        assert verify_session(None) is None

    def test_tampered_token_rejected(self):
        token = sign_session("alice")
        body = token.split(".")[1]
        flipped = ("A" if body[0] != "A" else "B") + body[1:]
        assert verify_session(token.replace(body, flipped)) is None

    def test_expired_token_rejected(self):
        now = time.time()
        token = sign_session("alice", now=now, ttl_seconds=10)
        assert verify_session(token, now=now + 5) == "alice"
        assert verify_session(token, now=now + 11) is None

    def test_expiry_reported(self):
        token = sign_session("alice", now=1000, ttl_seconds=100)
        assert token_expiry(token) == 1100


class TestAuthApi:
    def test_create_session_default_user(self, auth_client):
        resp = auth_client.post("/auth/session", json={})
        assert resp.status_code == 201
        body = resp.json()
        assert body["user_id"] == DEFAULT_USER_ID
        assert body["token"]
        assert isinstance(body["expires_at"], int)

    def test_create_session_named_user(self, auth_client):
        resp = auth_client.post("/auth/session", json={"user_id": "alice"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["user_id"] == "alice"
        assert verify_session(body["token"]) == "alice"

    def test_create_session_rejects_blank(self, auth_client):
        resp = auth_client.post("/auth/session", json={"user_id": "   "})
        assert resp.status_code == 422

    def test_me_falls_back_to_default_user(self, auth_client):
        resp = auth_client.get("/auth/me")
        assert resp.status_code == 200
        assert resp.json()["user_id"] == DEFAULT_USER_ID

    def test_me_with_bearer_token(self, auth_client):
        token = auth_client.post(
            "/auth/session", json={"user_id": "alice"}
        ).json()["token"]
        resp = auth_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "alice"

    def test_me_with_x_catchup_session_header(self, auth_client):
        token = auth_client.post(
            "/auth/session", json={"user_id": "alice"}
        ).json()["token"]
        resp = auth_client.get("/auth/me", headers={"X-Catchup-Session": token})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "alice"

    def test_me_with_tampered_token_falls_back(self, auth_client):
        token = auth_client.post(
            "/auth/session", json={"user_id": "alice"}
        ).json()["token"]
        body = token.split(".")[1]
        flipped = ("A" if body[0] != "A" else "B") + body[1:]
        resp = auth_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token.replace(body, flipped)}"}
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == DEFAULT_USER_ID

    def test_auth_required_rejects_anonymous_but_accepts_signed(
        self, auth_client, monkeypatch
    ):
        import app.api.deps as deps_mod
        import app.api.security as security_mod

        class _StrictSettings:
            AUTH_REQUIRED = True
            SESSION_SECRET = "test-secret"
            SESSION_TTL_SECONDS = 3600

        monkeypatch.setattr(deps_mod, "get_settings", lambda: _StrictSettings())
        monkeypatch.setattr(security_mod, "get_settings", lambda: _StrictSettings())

        assert auth_client.get("/auth/me").status_code == 401
        token = sign_session("alice")
        resp = auth_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "alice"