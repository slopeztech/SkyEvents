"""
Production settings for SkyEvents.

All secrets MUST come from environment variables.
This file enforces strict security defaults.

@file   config/settings/production.py
@author slopez.tech
"""

from __future__ import annotations

from .base import *  # noqa: F401, F403
from .base import env

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")  # Required — no default
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")  # Required — no default

# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31_536_000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 28800  # 8 hours

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# Database — require SSL in production
# ---------------------------------------------------------------------------
DATABASES = {  # type: ignore[assignment]
    "default": {
        **env.db("DATABASE_URL"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
        "OPTIONS": {
            "sslmode": "require",
            "connect_timeout": 10,
        },
    }
}

# ---------------------------------------------------------------------------
# File storage — S3-compatible (MinIO / AWS S3)
# ---------------------------------------------------------------------------
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="eu-west-1")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None  # Block public access; use signed URLs
AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default="")
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
AWS_QUERYSTRING_AUTH = True  # Signed URLs required
AWS_QUERYSTRING_EXPIRE = 3600  # 1 hour

# ---------------------------------------------------------------------------
# Email — SMTP
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

# ---------------------------------------------------------------------------
# CORS — explicit allowlist only
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

# ---------------------------------------------------------------------------
# Axes — strict in production
# ---------------------------------------------------------------------------
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # 1 hour
