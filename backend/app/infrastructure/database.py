"""Database session + engine setup.

All SQLAlchemy/database concerns live under infrastructure. Application services
never see a Session directly; they depend on repository interfaces that this
package implements.
"""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def _settings() -> object:
    return get_settings()


engine = create_engine(_settings().DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped database session.

    Commits successful request mutations and rolls back on failure so a partial
    write is never persisted. The generator's own exit path handles the commit
    once the request scope ends normally.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # noqa: BLE001 - roll back and re-raise for the handler
        session.rollback()
        raise
    finally:
        session.close()


def make_session() -> Session:
    return SessionLocal()
