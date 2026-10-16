from enum import StrEnum


class EventName(StrEnum):
    """Names of structured log events (ADR-0014). Use these instead of free-text messages."""

    REQUEST_COMPLETED = "request.completed"
    REQUEST_FAILED = "request.failed"
    GEOCODE_REQUESTED = "geocode.requested"
    PLAN_REQUESTED = "plan.requested"
    PLAN_COMPLETED = "plan.completed"
    PLAN_NO_SAFE_ROUTE = "plan.no_safe_route"
    ROUTES_FALLBACK_USED = "routes.fallback_used"
    WEATHER_REQUESTED = "weather.requested"
    PROVIDER_CALLED = "provider.called"
    PROVIDER_FAILED = "provider.failed"
    PROVIDER_QUOTA_EXCEEDED = "provider.quota_exceeded"
