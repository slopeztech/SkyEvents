"""
URL patterns for the camera app (dashboard CRUD).

@file   sky_events/apps/camera/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import path

from .views import (
    CameraCreateView,
    CameraDeleteView,
    CameraDetailView,
    CameraListView,
    CameraUpdateView,
)

app_name = "camera"

urlpatterns = [
    path("", CameraListView.as_view(), name="list"),
    path("new/", CameraCreateView.as_view(), name="create"),
    path("<str:code>/", CameraDetailView.as_view(), name="detail"),
    path("<str:code>/edit/", CameraUpdateView.as_view(), name="edit"),
    path("<str:code>/delete/", CameraDeleteView.as_view(), name="delete"),
]
