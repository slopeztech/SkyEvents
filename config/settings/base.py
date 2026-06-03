"""
Base Django settings for SkyEvents.

All environment-specific settings files inherit from this module.
Never import this file directly in production — use the appropriate
settings module (local / staging / production).

@file   config/settings/base.py
@author slopez.tech
"""

from __future__ import annotations

import environ
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# BASE_DIR  → project root  (SkyEvents/)
# APPS_DIR  → Django apps   (SkyEvents/sky_events/apps/)
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
APPS_DIR: Path = BASE_DIR / "sky_events"

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
env = environ.Env()

# Read .env only if the file exists (CI/CD may inject vars directly).
ENV_FILE: Path = BASE_DIR / ".env"
if ENV_FILE.exists():
    environ.Env.read_env(str(ENV_FILE))

# ---------------------------------------------------------------------------
# Security — NEVER override these with permissive values in base.py
# ---------------------------------------------------------------------------
SECRET_KEY: str = env("DJANGO_SECRET_KEY")
DEBUG: bool = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
DJANGO_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS: list[str] = [
    # REST Framework
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    # Filtering
    "django_filters",
    # Security
    "axes",
    "corsheaders",
    # Logging
    "django_structlog",
    # Async tasks
    "django_celery_beat",
    "django_celery_results",
    # Utilities
    "django_extensions",
]

LOCAL_APPS: list[str] = [
    "sky_events.apps.core",
    "sky_events.apps.users",
    "sky_events.apps.station",
    "sky_events.apps.camera",
    "sky_events.apps.radio",
    "sky_events.apps.notices",
    "sky_events.apps.events",
    "sky_events.apps.reports",
    "sky_events.apps.webconfig",
    # Web UI
    "theme",
    "sky_events.apps.web",
]

# ---------------------------------------------------------------------------
# Tailwind CSS
# ---------------------------------------------------------------------------
TAILWIND_APP_NAME: str = "theme"

INSTALLED_APPS: list[str] = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware — ORDER MATTERS
# ---------------------------------------------------------------------------
MIDDLEWARE: list[str] = [
    # Security headers (must be first)
    "django.middleware.security.SecurityMiddleware",
    # Whitenoise static files (after SecurityMiddleware)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # CORS (must be before CommonMiddleware)
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # i18n: detects language from Accept-Language header / session / cookie
    # Must be after SessionMiddleware and before CommonMiddleware
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Structured logging (must be after AuthenticationMiddleware)
    "django_structlog.middlewares.RequestMiddleware",
    # Brute-force protection (must be after AuthenticationMiddleware)
    "axes.middleware.AxesMiddleware",
]

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
ROOT_URLCONF: str = "config.urls"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES: list[dict] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [APPS_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "sky_events.apps.webconfig.context_processors.site_config",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# WSGI / ASGI
# ---------------------------------------------------------------------------
WSGI_APPLICATION: str = "config.wsgi.application"
ASGI_APPLICATION: str = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES: dict = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://skyevents:skyevents@localhost:5432/skyevents",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["OPTIONS"] = {
    "connect_timeout": 10,
}

# ---------------------------------------------------------------------------
# Custom user model
# ---------------------------------------------------------------------------
AUTH_USER_MODEL: str = "users.User"

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS: list[dict] = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Authentication backends
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS: list[str] = [
    # django-axes must be first to block locked accounts
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
# Active language list — add new tuples here to support more languages.
# The first language in the list is the fallback / default.
from django.utils.translation import gettext_lazy as _lazy  # noqa: E402

LANGUAGES: list[tuple[str, str]] = [
    ("en", _lazy("English")),
    ("es", _lazy("Spanish")),
]

LANGUAGE_CODE: str = "en"          # default language for the project
TIME_ZONE: str = "UTC"             # ALWAYS UTC — never change this
USE_I18N: bool = True
USE_L10N: bool = True              # localised date/number formatting
USE_TZ: bool = True                # ALWAYS True — all datetimes stored in UTC

# Directory that Django (and makemessages) scans for .po files.
# Add a new locale/XX/LC_MESSAGES/django.po to support language XX.
LOCALE_PATHS: list[Path] = [BASE_DIR / "locale"]

# ---------------------------------------------------------------------------
# Authentication — URLs
# ---------------------------------------------------------------------------
LOGIN_URL: str = "/login/"
LOGIN_REDIRECT_URL: str = "/dashboard/"
LOGOUT_REDIRECT_URL: str = "/"

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL: str = "/static/"
STATIC_ROOT: Path = BASE_DIR / "staticfiles"
STATICFILES_DIRS: list[Path] = [APPS_DIR / "static"]
STATICFILES_STORAGE: str = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ---------------------------------------------------------------------------
# Media files (local dev; overridden with S3 in production)
# ---------------------------------------------------------------------------
MEDIA_URL: str = "/media/"
MEDIA_ROOT: Path = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------
# All models use explicit UUIDField — this is a safety net only.
DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_URL: str = env("REDIS_URL", default="redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
CACHES: dict = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": False,
        },
        "KEY_PREFIX": "skyevents",
    }
}

# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
SESSION_ENGINE: str = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS: str = "default"
SESSION_COOKIE_HTTPONLY: bool = True
SESSION_COOKIE_SAMESITE: str = "Lax"

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL: str = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND: str = "django-db"
CELERY_RESULT_EXTENDED: bool = True
CELERY_CACHE_BACKEND: str = "default"
CELERY_TIMEZONE: str = "UTC"
CELERY_TASK_ALWAYS_EAGER: bool = False
CELERY_TASK_EAGER_PROPAGATES: bool = True
CELERY_TASK_SERIALIZER: str = "json"
CELERY_RESULT_SERIALIZER: str = "json"
CELERY_ACCEPT_CONTENT: list[str] = ["json"]
CELERY_BEAT_SCHEDULER: str = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_SOFT_TIME_LIMIT: int = 300   # 5 minutes
CELERY_TASK_TIME_LIMIT: int = 600        # 10 minutes hard limit

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK: dict = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # Session auth for the browsable API in development
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "sky_events.apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/hour",
        "user": "1000/hour",
        "station": "10000/hour",  # higher limit for station API key auth
        "ping": "12/minute",  # max 1 per 5 s per station; 12/min is the DRF-safe ceiling
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "sky_events.apps.core.exceptions.custom_exception_handler",
    # Datetime format — always ISO 8601 UTC
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%SZ",
    "DATETIME_INPUT_FORMATS": ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "iso-8601"],
    "DATE_FORMAT": "%Y-%m-%d",
    "TIME_FORMAT": "%H:%M:%S",
}

# ---------------------------------------------------------------------------
# JWT settings
# ---------------------------------------------------------------------------
from datetime import timedelta  # noqa: E402

SIMPLE_JWT: dict = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "sky_events.apps.users.serializers.TokenObtainPairSerializer",
}

# ---------------------------------------------------------------------------
# drf-spectacular (OpenAPI 3.1)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS: dict = {
    "TITLE": "SkyEvents API",
    "DESCRIPTION": (
        "REST API for SkyEvents — astronomical event management platform "
        "for automated observation stations."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "ENUM_GENERATE_CHOICE_DESCRIPTION": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
}

# ---------------------------------------------------------------------------
# django-axes (brute-force protection)
# ---------------------------------------------------------------------------
AXES_FAILURE_LIMIT: int = 5
AXES_COOLOFF_TIME: int = 1  # 1 hour lockout
AXES_RESET_ON_SUCCESS: bool = True
AXES_LOCKOUT_CALLABLE: str = "sky_events.apps.core.security.axes_lockout_response"
AXES_ENABLE_ADMIN: bool = True
AXES_VERBOSE: bool = False  # reduce noise in logs

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS: bool = False

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
DEFAULT_FROM_EMAIL: str = env("DEFAULT_FROM_EMAIL", default="noreply@skyevents.local")
SERVER_EMAIL: str = env("SERVER_EMAIL", default="server@skyevents.local")
EMAIL_SUBJECT_PREFIX: str = "[SkyEvents] "

# ---------------------------------------------------------------------------
# File upload security
# ---------------------------------------------------------------------------
FILE_UPLOAD_MAX_MEMORY_SIZE: int = 5 * 1024 * 1024       # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE: int = 5 * 1024 * 1024        # 5 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS: int = 1000
MEDIA_MAX_UPLOAD_SIZE: int = env.int(
    "MEDIA_MAX_UPLOAD_SIZE", default=500 * 1024 * 1024    # 500 MB for videos
)

# ---------------------------------------------------------------------------
# Structured logging (structlog)
# ---------------------------------------------------------------------------
LOGGING: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processors": [
                "structlog.contextvars.merge_contextvars",
                "structlog.stdlib.add_log_level",
                "structlog.stdlib.add_logger_name",
                "structlog.stdlib.PositionalArgumentsFormatter",
                "structlog.processors.TimeStamper",
                "structlog.processors.StackInfoRenderer",
                "structlog.stdlib.ProcessorFormatter.wrap_for_formatter",
            ],
            "foreign_pre_chain": [
                "structlog.contextvars.merge_contextvars",
                "structlog.stdlib.add_log_level",
                "structlog.stdlib.add_logger_name",
                "structlog.processors.TimeStamper",
            ],
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "sky_events": {
            "handlers": ["console"],
            "level": env("APP_LOG_LEVEL", default="DEBUG"),
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------
SENTRY_DSN: str = env("SENTRY_DSN", default="")

if SENTRY_DSN:
    import sentry_sdk  # noqa: PLC0415
    from sentry_sdk.integrations.celery import CeleryIntegration  # noqa: PLC0415
    from sentry_sdk.integrations.django import DjangoIntegration  # noqa: PLC0415
    from sentry_sdk.integrations.redis import RedisIntegration  # noqa: PLC0415

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style="url"),
            CeleryIntegration(monitor_beat_tasks=True),
            RedisIntegration(),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,  # GDPR compliance
        environment=env("SENTRY_ENVIRONMENT", default="development"),
    )

# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
ADMIN_URL: str = env("DJANGO_ADMIN_URL", default="admin/")
