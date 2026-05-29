"""
Local development settings for SkyEvents.

Extends base settings with developer-friendly defaults:
- DEBUG enabled
- SQLite-like relaxed password requirements
- django-debug-toolbar
- Email to console
- No external services required

@file   config/settings/local.py
@author slopez.tech
"""

from __future__ import annotations

from .base import *  # noqa: F401, F403
from .base import INSTALLED_APPS, MIDDLEWARE, env

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = env("DJANGO_SECRET_KEY", default="local-insecure-secret-key-change-me-in-env")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "0.0.0.0"])  # noqa: S104

# ---------------------------------------------------------------------------
# WhiteNoise — reload static files from disk on every request in development
# so CSS/JS changes after collectstatic are immediately visible without restart.
# ---------------------------------------------------------------------------
WHITENOISE_AUTOREFRESH = True

# ---------------------------------------------------------------------------
# Debug toolbar
# ---------------------------------------------------------------------------
INSTALLED_APPS += ["debug_toolbar", "django_browser_reload", "tailwind"]  # type: ignore[name-defined]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    *MIDDLEWARE,
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]

# Support Docker internal IPs for debug toolbar
import socket  # noqa: E402

try:
    _, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [ip[: ip.rfind(".")] + ".1" for ip in ips]
except OSError:
    pass

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# Password validation — relaxed for development
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = []  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Celery — run tasks eagerly in development if needed
# ---------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)

# ---------------------------------------------------------------------------
# CORS — allow all origins in local development
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True

# ---------------------------------------------------------------------------
# Cache — use in-memory cache; no Redis required locally
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "skyevents-local",
    }
}

# Sessions backed by the DB so Redis is not required locally
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ---------------------------------------------------------------------------
# REST Framework — add browsable API in development
# ---------------------------------------------------------------------------
from .base import REST_FRAMEWORK  # noqa: E402

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# ---------------------------------------------------------------------------
# Axes — relaxed in development
# ---------------------------------------------------------------------------
AXES_ENABLED = False

# ---------------------------------------------------------------------------
# Logging — verbose in development
# ---------------------------------------------------------------------------
LOGGING = {  # type: ignore[assignment]
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.db.backends": {
            "handlers": ["console"],
            "level": env("DJANGO_DB_LOG_LEVEL", default="WARNING"),
            "propagate": False,
        },
        "sky_events": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
