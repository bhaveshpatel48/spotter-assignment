"""Application errors. Plain Python, so any layer can raise them.

The DRF exception handler turns them into the API error format.
"""


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    default_message = "Something went wrong."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class TripOutsideForecastRange(AppError):
    status_code = 400
    code = "TRIP_OUTSIDE_FORECAST_RANGE"
    default_message = (
        "The trip extends beyond the available weather forecast. Choose an earlier departure."
    )


class NoRouteFound(AppError):
    status_code = 404
    code = "NO_ROUTE_FOUND"
    default_message = "No truck route was found between these locations."


class ProviderError(AppError):
    status_code = 502
    code = "PROVIDER_ERROR"
    default_message = "An external service failed. Please try again."


class ProviderQuotaExceeded(AppError):
    status_code = 503
    code = "PROVIDER_QUOTA_EXCEEDED"
    default_message = "An external service's free quota is used up. Please try again later."


class ProviderNotConfigured(AppError):
    status_code = 503
    code = "PROVIDER_NOT_CONFIGURED"
    default_message = "An external service is not configured on the server."


class ProviderTimeout(AppError):
    status_code = 504
    code = "PROVIDER_TIMEOUT"
    default_message = "An external service did not respond in time. Please try again."
