"""Retry helper with exponential backoff.

Used by the Yahoo provider to tolerate transient failures. Timeouts and delays
are configurable so tests can run fast.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import TypeVar

from app.domain.enums import ProviderFailure
from app.market_data.data_types import ProviderResult

T = TypeVar("T")

logger = logging.getLogger(__name__)

DEFAULT_BACKOFF_SECONDS = (1, 2, 4)


def retry_provider_call(
    fn: Callable[[], T],
    *,
    max_retries: int = 3,
    backoff_seconds: tuple[float, ...] = DEFAULT_BACKOFF_SECONDS,
    timeout_seconds: float = 10.0,
    source: str,
) -> ProviderResult[T]:
    """Invoke a provider call with retries and classification.

    Re-raises nothing; always returns a ProviderResult. Transient provider
    exceptions are retried with exponential backoff; persistent failures are
    classified and surfaced for downstream fallback handling.
    """
    import time as _time

    last_failure: ProviderFailure = ProviderFailure.UNKNOWN
    last_message: str | None = None
    started = _time.perf_counter()
    deadline = started + timeout_seconds

    for attempt in range(1, max_retries + 1):
        try:
            remaining = deadline - _time.perf_counter()
            if remaining <= 0:
                raise TimeoutError("provider call exceeded timeout budget")
            value = _call_with_timeout(fn, remaining)
            latency = int((_time.perf_counter() - started) * 1000)
            return ProviderResult.success(value, latency_ms=latency)
        except Exception as exc:  # noqa: BLE001 - we classify all provider errors
            last_message = str(exc)
            last_failure = _classify(exc)
            logger.warning(
                "provider=%s attempt=%d/%d failed: %s",
                source,
                attempt,
                max_retries,
                last_message,
            )
            # Enforce the caller's timeout: a bounded overall budget prevents a
            # slow/stuck provider from retrying indefinitely across cycles.
            if _time.perf_counter() >= deadline:
                last_failure = ProviderFailure.TIMEOUT
                last_message = last_message or "provider call exceeded timeout"
                logger.error(
                    "provider=%s timed out after %.2fs: %s",
                    source,
                    timeout_seconds,
                    last_message,
                )
                return ProviderResult.failed(
                    last_failure, message=last_message, latency_ms=_elapsed_ms(started)
                )
            if attempt < max_retries:
                delay = backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)]
                # Cap the sleep so it never pushes past the deadline.
                remaining = deadline - _time.perf_counter()
                delay = min(delay, max(0.0, remaining))
                _time.sleep(delay)

    latency = int((_time.perf_counter() - started) * 1000)
    logger.error(
        "provider=%s permanently failed after %d attempts: %s",
        source,
        max_retries,
        last_message,
    )
    return ProviderResult.failed(last_failure, message=last_message, latency_ms=latency)


def _elapsed_ms(started: float) -> int:
    import time as t
    return int((t.perf_counter() - started) * 1000)


def _call_with_timeout(fn: Callable[[], T], timeout_seconds: float) -> T:
    """Bound the caller's wait even when an SDK exposes no timeout option.

    Python cannot safely kill a blocked third-party thread, but shutting the
    executor down without waiting guarantees an ingestion worker is never held
    hostage by that call. SDK-specific timeouts should still be passed where
    supported; this is the final safety boundary.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeoutError as exc:
        future.cancel()
        raise TimeoutError("provider call exceeded timeout budget") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _classify(exc: Exception) -> ProviderFailure:
    import socket

    if isinstance(exc, socket.timeout) or isinstance(exc, TimeoutError):
        return ProviderFailure.TIMEOUT
    if isinstance(exc, (ConnectionError, OSError)):
        return ProviderFailure.NETWORK
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return ProviderFailure.INVALID_DATA
    return ProviderFailure.UNKNOWN
