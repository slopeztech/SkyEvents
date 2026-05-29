"""
Root URL configuration for SkyEvents.

URL structure:
    /admin/                 → Django admin
    /health/                → Liveness probe
    /live/                  → Kubernetes liveness
    /ready/                 → Readiness probe (checks DB + Redis)
    /api/v1/                → REST API v1
    /api/schema/            → OpenAPI 3.1 schema (JSON)
    /api/docs/              → Swagger UI
    /api/redoc/             → ReDoc UI
    /__debug__/             → django-debug-toolbar (dev only)

@file   config/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# ---------------------------------------------------------------------------
# Core (health checks) + Admin
# ---------------------------------------------------------------------------
urlpatterns = [
    # Admin — URL is configurable via ADMIN_URL env var
    path(settings.ADMIN_URL, admin.site.urls),
    # i18n set_language view (used by language switcher)
    path("i18n/", include("django.conf.urls.i18n")),
    # Health / readiness probes
    path("", include("sky_events.apps.core.urls", namespace="core")),
    # Web UI (public pages + dashboards)
    path("", include("sky_events.apps.web.urls", namespace="web")),
    # Public event notices
    path("", include("sky_events.apps.notices.urls", namespace="notices")),
    # Astronomical events
    path("", include("sky_events.apps.events.urls", namespace="events")),
    # Admin CRUD — network devices
    path("stations/", include("sky_events.apps.station.urls")),
    path("cameras/", include("sky_events.apps.camera.urls")),
    path("radios/", include("sky_events.apps.radio.urls")),
    # Admin CRUD — user management
    path("accounts/", include("sky_events.apps.users.dashboard_urls")),
    # Station detection reports
    path("reports/", include("sky_events.apps.reports.urls")),
    # Site-wide web configuration (admin only)
    path("webconfig/", include("sky_events.apps.webconfig.urls")),
    # API v1 — central router (JWT auth + station script endpoints)
    path("api/v1/", include("sky_events.apps.core.api.urls")),
    # OpenAPI schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# ---------------------------------------------------------------------------
# Development-only URLs
# ---------------------------------------------------------------------------
if settings.DEBUG:
    # django-debug-toolbar
    try:
        import debug_toolbar  # noqa: F401

        urlpatterns = [
            path("__debug__/", include("debug_toolbar.urls")),
            *urlpatterns,
        ]
    except ImportError:
        pass

    # django-browser-reload (hot reload in development)
    try:
        urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]
    except Exception:  # noqa: BLE001
        pass

    # Serve media files locally in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
