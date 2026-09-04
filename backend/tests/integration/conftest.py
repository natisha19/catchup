"""Disposable-PostgreSQL integration test fixtures.

Spins up a throwaway Postgres container (using the Docker CLI), runs the real
Alembic migrations against it, and exposes plumbing so tests exercise the real
repositories, services, and the FastAPI app against a real database.

These tests are excluded from the default run (pytest.ini `norecursedirs`
ignores `tests/integration`), so `python -m pytest tests/` stays green without
Docker. Run the real-DB suite explicitly:

    $env:CATCHUP_RUN_INTEGRATION=1; python -m pytest tests/integration -v
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
import uuid

import psycopg2
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

POSTGRES_IMAGE = os.environ.get("CATCHUP_PG_IMAGE", "postgres:16-alpine")
RUN_INTEGRATION = os.environ.get("CATCHUP_RUN_INTEGRATION") == "1"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_ready(port: int, password: str, timeout: float = 90.0) -> None:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=port,
                user="postgres",
                password=password,
                dbname="postgres",
                connect_timeout=2,
            )
            conn.close()
            return
        except Exception as err:  # noqa: BLE001 - readiness probe
            last_err = err
            time.sleep(1)
    raise RuntimeError(f"Postgres container did not become ready: {last_err}")


@pytest.fixture(scope="session")
def pg_container():
    """Start and later remove a disposable Postgres container."""
    if not RUN_INTEGRATION:
        pytest.skip("set CATCHUP_RUN_INTEGRATION=1 to run Postgres integration tests")

    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        pytest.skip("Docker is not available; cannot run integration tests")

    port = _free_port()
    name = f"catchup-it-{uuid.uuid4().hex[:8]}"
    password = "catchup_int_pw"

    proc = subprocess.run(
        [
            "docker", "run", "-d", "--name", name,
            "-e", f"POSTGRES_PASSWORD={password}",
            "-p", f"127.0.0.1:{port}:5432",
            POSTGRES_IMAGE,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        pytest.fail(f"docker run failed: {proc.stderr.strip()}")

    try:
        _wait_ready(port, password)
        host_url = f"postgresql+psycopg2://postgres:{password}@127.0.0.1:{port}/postgres"
        yield {"host_url": host_url, "port": port, "name": name}
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


def _backend_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migrations(database_url: str) -> str:
    """Run `python -m alembic upgrade head` against `database_url` (subprocess).

    A subprocess is used deliberately: alembic/env.py reads the SQLAlchemy URL
    from the module-level cached `app.config.get_settings()`, so it must run in
    a fresh process with DATABASE_URL set. This is also the exact command used
    to provision a real database.
    """
    env = dict(os.environ)
    env["DATABASE_URL"] = database_url
    env.pop("PYTEST_CURRENT_TEST", None)
    result = subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic upgrade failed:\n{result.stdout}\n{result.stderr}"
    return result.stdout


@pytest.fixture(scope="session")
def test_engine(pg_container):
    """SQLAlchemy engine bound to the disposable database."""
    engine = create_engine(pg_container["host_url"], pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def migrated(test_engine, pg_container):
    """Apply the real Alembic migration chain to the disposable database.

    Runs `python -m alembic upgrade head` in a subprocess with DATABASE_URL set
    — the exact command documented for provisioning a database — so it exercises
    the same code path a deployment would use. It bypasses the module-level
    cached settings in app.config intentionally.
    """
    run_migrations(pg_container["host_url"])

    with test_engine.begin() as conn:
        tables = set(
            conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            )).scalars()
        )
    assert "instruments" in tables
    assert "watchlist_items" in tables
    assert "market_snapshots" in tables
    assert "change_signals" in tables
    assert "corporate_events" in tables
    assert "user_last_seen" in tables
    assert "alembic_version" in tables

    with test_engine.begin() as conn:
        has_partial = conn.execute(text(
            "SELECT indexdef FROM pg_indexes WHERE indexname='uq_watchlist_item_active'"
        )).fetchone()
    assert has_partial is not None
    assert "removed_at IS NULL" in has_partial[0]
    return pg_container


@pytest.fixture(scope="session")
def run_migrations_fixture():
    return run_migrations


@pytest.fixture(autouse=True)
def _clean_db(db_session_factory):
    """Reset every table before each test so tests are fully isolated.

    The disposable database is reused for the whole session; without a clean
    start, data written by one test leaks into the next (e.g. watchlists
    accumulating instruments). Truncate with identity restart + cascade.
    """
    session = db_session_factory()
    try:
        session.execute(text("SET session_replication_role = replica"))
        for table in [
            "change_signals",
            "market_snapshots",
            "corporate_events",
            "watchlist_items",
            "watchlists",
            "user_last_seen",
            "instruments",
        ]:
            session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        session.execute(text("SET session_replication_role = DEFAULT"))
        session.commit()
    finally:
        session.close()


@pytest.fixture(scope="session")
def db_session_factory(migrated, test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session(db_session_factory):
    session = db_session_factory()
    try:
        yield session
    finally:
        session.close()
