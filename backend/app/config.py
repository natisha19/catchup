"""Application configuration.

All environment-specific values live here, read from environment variables.
Nothing in the codebase should hardcode environment-specific thresholds or
connection strings.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/catchup"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Market data provider
    PROVIDER_TIMEOUT_SECONDS: float = 10.0
    PROVIDER_MAX_RETRIES: int = 3

    # Ingestion
    INGESTION_INTERVAL_SECONDS: int = 300
    INGESTION_ENABLED: bool = False

    # Freshness policy (minutes)
    DELAYED_THRESHOLD_MINUTES: int = 5
    STALE_THRESHOLD_MINUTES: int = 30

    # Baseline configuration (trading days)
    BASELINE_WINDOW_DAYS: int = 30
    MIN_BASELINE_RETURNS: int = 20
    LIMITED_BASELINE_RETURNS: int = 5

    # Significance thresholds. Percentage returns are absolute values.
    PRICE_NOTABLE_THRESHOLD: float = 2.0
    PRICE_SIGNIFICANT_THRESHOLD: float = 4.0
    PRICE_CRITICAL_THRESHOLD: float = 7.0
    PRICE_NOTABLE_Z: float = 1.5
    PRICE_SIGNIFICANT_Z: float = 2.0
    PRICE_CRITICAL_Z: float = 3.0

    # Volume thresholds (ratio of current / baseline average).
    VOLUME_NOTABLE_RATIO: float = 2.0
    VOLUME_SIGNIFICANT_RATIO: float = 3.0

    LOG_LEVEL: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
