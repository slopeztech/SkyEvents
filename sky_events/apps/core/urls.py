"""
URL patterns for the core application.

@file   sky_events/apps/core/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import path

from sky_events.apps.core.views import HealthCheckView, ReadinessCheckView

app_name = "core"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("live/", HealthCheckView.as_view(), name="live"),
    path("ready/", ReadinessCheckView.as_view(), name="ready"),
]
