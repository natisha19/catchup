"""Provider retry safety tests."""

from __future__ import annotations

import time

from app.domain.enums import ProviderFailure
from app.market_data.retry import retry_provider_call


def test_retries_a_transient_failure_then_returns_value():
    attempts = 0

    def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionError("temporary")
        return "ok"

    result = retry_provider_call(
        flaky, max_retries=2, backoff_seconds=(0,), timeout_seconds=1, source="test"
    )

    assert result.ok is True
    assert result.value == "ok"
    assert attempts == 2


def test_returns_timeout_without_waiting_for_a_blocked_provider_call():
    def blocked() -> str:
        time.sleep(0.2)
        return "too late"

    started = time.perf_counter()
    result = retry_provider_call(
        blocked, max_retries=1, timeout_seconds=0.02, source="test"
    )

    assert result.ok is False
    assert result.failure is ProviderFailure.TIMEOUT
    assert time.perf_counter() - started < 0.15
