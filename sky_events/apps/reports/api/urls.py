"""
URL patterns for the station-script API.

Mounted under /api/v1/station/ by sky_events/apps/core/api/urls.py.

@file   sky_events/apps/reports/api/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path(
        "reports/",
        views.StationReportCreateAPIView.as_view(),
        name="station-report-create",
    ),
    path(
        "ping/",
        views.StationPingAPIView.as_view(),
        name="station-ping",
    ),
    path(
        "requirements/",
        views.MediaRequirementListAPIView.as_view(),
        name="station-requirement-list",
    ),
    path(
        "requirements/<uuid:pk>/media/",
        views.ReportAttachmentUploadAPIView.as_view(),
        name="station-requirement-media",
    ),
]
