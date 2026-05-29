"""
Serializers for the users application.

Includes a custom TokenObtainPairSerializer that injects user information
into the JWT payload for use by API consumers.

@file   sky_events/apps/users/serializers.py
@author slopez.tech
"""

from __future__ import annotations

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as BaseSerializer
from rest_framework_simplejwt.tokens import Token

from sky_events.apps.users.models import User


class TokenObtainPairSerializer(BaseSerializer):
    """
    Custom JWT token serializer.

    Adds user metadata to the token payload so API consumers can
    identify the user without an extra /me request.

    Added claims:
    - ``email``
    - ``username``
    - ``role``
    - ``is_staff``
    """

    @classmethod
    def get_token(cls, user: User) -> Token:  # type: ignore[override]
        """
        Generate a token with additional SkyEvents-specific claims.

        @param  user    The authenticated User instance.
        @return A JWT token with extra claims.
        """
        token = super().get_token(user)  # type: ignore[arg-type]

        # Add custom claims — keep these minimal (JWT is sent on every request)
        token["email"] = user.email
        token["username"] = user.username
        token["role"] = user.role
        token["is_staff"] = user.is_staff

        return token
