"""
URL patterns for user management dashboard (admin only).

@file   sky_events/apps/users/dashboard_urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import path

from .dashboard_views import (
    ScriptDataView,
    UserCreateView,
    UserDetailView,
    UserListView,
    UserToggleActiveView,
    UserUpdateView,
)

app_name = "accounts"

urlpatterns = [
    path("", UserListView.as_view(), name="list"),
    path("new/", UserCreateView.as_view(), name="create"),
    path("<uuid:pk>/", UserDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", UserUpdateView.as_view(), name="edit"),
    path("<uuid:pk>/toggle-active/", UserToggleActiveView.as_view(), name="toggle-active"),
    path("<uuid:pk>/script-data/", ScriptDataView.as_view(), name="script-data"),
]
