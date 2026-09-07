"""Cron ingestion endpoint tests.

The success path can't run in unit tests (it would hit a real provider and
database), so we verify the authorization rules with a stubbed tick and keep the
default-disabled behavior as the contract.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app

client = TestClient(app)


def test_cron_ingest_disabled_without_secret():
    response = client.post("/cron/ingest")
    assert response.status_code == 403


def test_cron_ingest_requires_matching_secret(monkeypatch):
    settings = Settings(CRON_SECRET="topsecret")
    monkeypatch.setattr("app.api.cron.get_settings", lambda: settings)

    def fake_tick(enrich: bool, instrument_ids=None):
        return (
            type(
                "Q",
                (),
                {"instruments": 1, "snapshots": 2, "invalid": 0, "provider_failures": 0},
            )(),
            None,
        )

    monkeypatch.setattr("app.api.cron.run_tick", fake_tick)

    assert client.post("/cron/ingest").status_code == 403
    assert client.post("/cron/ingest", headers={"x-cron-secret": "wrong"}).status_code == 403

    response = client.post("/cron/ingest", headers={"x-cron-secret": "topsecret"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_cron_ingest_accepts_vercel_header(monkeypatch):
    settings = Settings(CRON_SECRET="topsecret")
    monkeypatch.setattr("app.api.cron.get_settings", lambda: settings)

    calls = []

    def fake_tick(enrich: bool, instrument_ids=None):
        calls.append((enrich, instrument_ids))
        return (
            type(
                "Q",
                (),
                {"instruments": 1, "snapshots": 2, "invalid": 0, "provider_failures": 0},
            )(),
            None,
        )

    monkeypatch.setattr("app.api.cron.run_tick", fake_tick)

    response = client.post("/cron/ingest", headers={"x-vercel-cron": "1"})
    assert response.status_code == 200
    assert calls and calls[0][0] is True