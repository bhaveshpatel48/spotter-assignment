"""Shared HTTP client for external services: timeouts, one retry, and provider.called events."""

import time

import httpx
import structlog

from core.errors import ProviderError, ProviderQuotaExceeded, ProviderTimeout
from core.events import EventName

logger = structlog.get_logger(__name__)

TIMEOUT = httpx.Timeout(10.0, connect=5.0)
RETRY_STATUSES = {500, 502, 503, 504}
QUOTA_STATUSES = {403, 429}

# One pooled client for the process; httpx clients are safe to share between threads.
_client = httpx.Client(timeout=TIMEOUT)


def send(provider: str, endpoint: str, method: str, url: str, **kwargs) -> httpx.Response:
    """Send a request, retrying once on connection errors and 5xx responses.

    `endpoint` is a short label for logs; the URL is never logged because it may hold an API key.
    """
    for attempt in (1, 2):
        started = time.perf_counter()
        try:
            response = _client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            _log_failure(provider, endpoint, "timeout", attempt)
            raise ProviderTimeout() from exc
        except httpx.TransportError as exc:
            _log_failure(provider, endpoint, type(exc).__name__, attempt)
            if attempt == 1:
                continue
            raise ProviderError() from exc

        logger.info(
            EventName.PROVIDER_CALLED,
            provider=provider,
            endpoint=endpoint,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000),
            attempt=attempt,
        )
        if response.status_code in RETRY_STATUSES and attempt == 1:
            continue
        return response
    raise AssertionError("unreachable")


def raise_for_status(provider: str, endpoint: str, response: httpx.Response) -> None:
    """Map unsuccessful responses to application errors."""
    if response.is_success:
        return
    if response.status_code in QUOTA_STATUSES:
        logger.warning(
            EventName.PROVIDER_QUOTA_EXCEEDED,
            provider=provider,
            endpoint=endpoint,
            status=response.status_code,
        )
        if response.status_code == 429:
            raise ProviderQuotaExceeded(
                "An external service's rate limit was reached. Please try again in a minute."
            )
        raise ProviderQuotaExceeded()
    _log_failure(provider, endpoint, f"http_{response.status_code}", attempt=None)
    raise ProviderError()


def _log_failure(provider: str, endpoint: str, error_type: str, attempt: int | None) -> None:
    logger.warning(
        EventName.PROVIDER_FAILED,
        provider=provider,
        endpoint=endpoint,
        error_type=error_type,
        attempt=attempt,
    )
