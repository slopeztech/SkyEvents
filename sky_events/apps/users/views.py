"""
Views for the users application.

Thin views — business logic lives in services, not here.

@file   sky_events/apps/users/views.py
@author slopez.tech
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenView

from sky_events.apps.users.serializers import TokenObtainPairSerializer
from sky_events.apps.users.user_serializers import UserProfileSerializer


class TokenObtainPairView(BaseTokenView):
    """
    Obtain JWT access + refresh token pair.

    POST /api/v1/auth/token/

    Request body::

        { "email": "user@example.com", "password": "secret" }

    Response::

        { "access": "...", "refresh": "..." }
    """

    serializer_class = TokenObtainPairSerializer


class UserMeView(APIView):
    """
    Return the profile of the currently authenticated user.

    GET /api/v1/auth/me/

    Requires: Bearer token authentication.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user profile",
        responses={200: UserProfileSerializer},
        tags=["Auth"],
    )
    def get(self, request: Request) -> Response:
        """Return the authenticated user's profile."""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
