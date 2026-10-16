import time
import uuid

import structlog

from core.events import EventName

REQUEST_ID_HEADER = "X-Request-ID"

logger = structlog.get_logger(__name__)


class RequestIDMiddleware:
    """Gives every request a UUID, adds it to every log line and to the response header,
    and logs one `request.completed` event per request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = _valid_uuid(request.headers.get(REQUEST_ID_HEADER)) or str(uuid.uuid4())
        request.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        try:
            response = self.get_response(request)
            response[REQUEST_ID_HEADER] = request_id
            logger.info(
                EventName.REQUEST_COMPLETED,
                method=request.method,
                path=request.path,
                status=response.status_code,
                duration_ms=round((time.perf_counter() - started) * 1000),
            )
            return response
        finally:
            structlog.contextvars.clear_contextvars()


def _valid_uuid(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(uuid.UUID(value))
    except ValueError:
        return None
