"""Turns every error into one JSON shape: {"error": {"code", "message", "request_id"}}."""

import structlog
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from core.errors import AppError
from core.events import EventName

logger = structlog.get_logger(__name__)


def handle_exception(exc, context):
    request_id = structlog.contextvars.get_contextvars().get("request_id")

    if isinstance(exc, AppError):
        logger.warning(EventName.REQUEST_FAILED, code=exc.code, message=exc.message)
        return _error(exc.status_code, exc.code, exc.message, request_id)

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception(EventName.REQUEST_FAILED, code="INTERNAL_ERROR")
        return _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "Something went wrong.",
            request_id,
        )

    if isinstance(exc, ValidationError):
        return _error(
            response.status_code,
            "VALIDATION_ERROR",
            "The request is invalid.",
            request_id,
            fields=response.data,
        )

    code = str(getattr(exc, "default_code", "error")).upper()
    return _error(response.status_code, code, str(getattr(exc, "detail", exc)), request_id)


def _error(status_code: int, code: str, message: str, request_id: str | None, **extra) -> Response:
    body = {"code": code, "message": message, "request_id": request_id, **extra}
    return Response({"error": body}, status=status_code)
