"""
Test settings for SkyEvents.

Optimised for fast test execution:
- SQLite in-memory database by default (can override with PostgreSQL)
- Celery always eager
- No external services
- Minimal logging noise

@file   config/settings/test.py
@author slopez.tech
"""

from __future__ import annotations

from .base import *  # noqa: F401, F403
from .base import env

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = False
SECRET_KEY = "test-insecure-secret-key-do-not-use-outside-tests"  # noqa: S105
ALLOWED_HOSTS = ["localhost", "testserver"]

# ---------------------------------------------------------------------------
# Database — use PostgreSQL for integration tests (mirrors production)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("TEST_DB_NAME", default="skyevents_test"),
        "USER": env("TEST_DB_USER", default="skyevents"),
        "PASSWORD": env("TEST_DB_PASSWORD", default="skyevents"),
        "HOST": env("TEST_DB_HOST", default="localhost"),
        "PORT": env("TEST_DB_PORT", default="5432"),
        "TEST": {
            "NAME": env("TEST_DB_NAME", default="skyevents_test"),
        },
    }
}

# ---------------------------------------------------------------------------
# Celery — always synchronous in tests
# ---------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ---------------------------------------------------------------------------
# Cache — use local-memory cache (no Redis needed)
# ---------------------------------------------------------------------------
CACHES = {  # type: ignore[assignment]
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ---------------------------------------------------------------------------
# Password hashing — use fast hasher for tests
# ---------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ---------------------------------------------------------------------------
# Media files
# ---------------------------------------------------------------------------
import tempfile  # noqa: E402

MEDIA_ROOT = tempfile.mkdtemp()

# ---------------------------------------------------------------------------
# Axes — disable in tests to avoid lockout issues
# ---------------------------------------------------------------------------
AXES_ENABLED = False

# ---------------------------------------------------------------------------
# Logging — suppress during tests
# ---------------------------------------------------------------------------
LOGGING = {  # type: ignore[assignment]
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"]},
}

# ---------------------------------------------------------------------------
# Static / WhiteNoise — disable manifest storage in tests
# ---------------------------------------------------------------------------
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
