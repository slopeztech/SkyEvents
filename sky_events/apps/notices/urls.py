"""
URL configuration for the notices app.

@file   sky_events/apps/notices/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "notices"

urlpatterns = [
    path("report/", views.SubmitNoticeView.as_view(), name="submit"),
]
