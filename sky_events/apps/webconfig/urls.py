"""
URL configuration for the webconfig app.

@file   sky_events/apps/webconfig/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import path

from .views import WebConfigView

app_name = "webconfig"

urlpatterns = [
    path("", WebConfigView.as_view(), name="edit"),
]
