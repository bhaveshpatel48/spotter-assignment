"""Django settings. Every deploy-specific value comes from environment variables."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from core.logging import configure_structlog, logging_config

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DEBUG = env_bool("DEBUG")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DEBUG is off.")
    SECRET_KEY = "insecure-local-development-key"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
if render_host := os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(render_host)

# No admin, auth or sessions: the app is anonymous and stores nothing (ADR-0012).
INSTALLED_APPS = [
    "corsheaders",
    "rest_framework",
    "api",
]

MIDDLEWARE = [
    "core.middleware.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Configured but unused: Django and its test tools expect a database (ADR-0012).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# In-process cache shared by the threads of the single Gunicorn worker (ADR-0013).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "OPTIONS": {"MAX_ENTRIES": 20_000},
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "core.exception_handler.handle_exception",
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_EXPOSE_HEADERS = ["X-Request-ID"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True

TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY", "")

configure_structlog()
LOGGING = logging_config(
    log_format=os.environ.get("LOG_FORMAT", "console"),
    level=os.environ.get("LOG_LEVEL", "INFO"),
)
