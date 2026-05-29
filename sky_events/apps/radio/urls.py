"""
URL patterns for the radio app (dashboard CRUD).

@file   sky_events/apps/radio/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import path

from .views import (
    RadioCreateView,
    RadioDeleteView,
    RadioDetailView,
    RadioListView,
    RadioUpdateView,
)

app_name = "radio"

urlpatterns = [
    path("", RadioListView.as_view(), name="list"),
    path("new/", RadioCreateView.as_view(), name="create"),
    path("<str:code>/", RadioDetailView.as_view(), name="detail"),
    path("<str:code>/edit/", RadioUpdateView.as_view(), name="edit"),
    path("<str:code>/delete/", RadioDeleteView.as_view(), name="delete"),
]
