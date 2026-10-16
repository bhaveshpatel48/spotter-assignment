"""structlog setup shared by Django, Gunicorn and our code (ADR-0014)."""

import structlog

SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
]


def configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *SHARED_PROCESSORS,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def logging_config(log_format: str, level: str) -> dict:
    """Django LOGGING setting. `log_format` is "json" (Docker, Render) or "console" (local)."""
    if log_format == "json":
        renderer = [structlog.processors.dict_tracebacks, structlog.processors.JSONRenderer()]
    else:
        renderer = [structlog.dev.ConsoleRenderer()]

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structlog": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    *renderer,
                ],
                "foreign_pre_chain": SHARED_PROCESSORS,
            },
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "structlog"},
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            # Our middleware logs every request, so Django's own request logs are redundant.
            "django.request": {"level": "ERROR"},
            "django.server": {"level": "ERROR"},
        },
    }
