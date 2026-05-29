"""
Central URL router for API v1.

All versioned API paths are aggregated here so that ``config/urls.py``
only needs a single ``include``.

Endpoints
---------
/api/v1/auth/token/                 POST  — obtain JWT pair
/api/v1/auth/token/refresh/         POST  — refresh access token
/api/v1/auth/token/verify/          POST  — verify token validity
/api/v1/auth/me/                    GET   — current user info

/api/v1/station/reports/            POST  — station creates a report
/api/v1/station/requirements/       GET   — list pending file requirements
/api/v1/station/requirements/{id}/media/  POST  — upload a required file

@file   sky_events/apps/core/api/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    # JWT authentication + user-info endpoints (namespace "users" comes
    # from app_name = "users" defined inside sky_events.apps.users.urls)
    path("", include("sky_events.apps.users.urls")),
    # Station-script API
    path("station/", include("sky_events.apps.reports.api.urls")),
]
