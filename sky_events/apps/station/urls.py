"""
URL patterns for the station app (dashboard CRUD).

@file   sky_events/apps/station/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import path

from .views import (
    StationCreateView,
    StationDeleteView,
    StationDetailView,
    StationListView,
    StationUpdateView,
)

app_name = "station"

urlpatterns = [
    path("", StationListView.as_view(), name="list"),
    path("new/", StationCreateView.as_view(), name="create"),
    path("<str:code>/", StationDetailView.as_view(), name="detail"),
    path("<str:code>/edit/", StationUpdateView.as_view(), name="edit"),
    path("<str:code>/delete/", StationDeleteView.as_view(), name="delete"),
]
