"""
URL patterns for the users application.

Provides JWT authentication endpoints.

@file   sky_events/apps/users/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from sky_events.apps.users.views import TokenObtainPairView, UserMeView

app_name = "users"

urlpatterns = [
    # JWT token endpoints
    path("auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    # Current user info
    path("auth/me/", UserMeView.as_view(), name="user-me"),
]
