"""
User profile serializers for read operations.

Separated from auth serializers to maintain single responsibility.

@file   sky_events/apps/users/user_serializers.py
@author slopez.tech
"""

from __future__ import annotations

from rest_framework import serializers

from sky_events.apps.users.models import User


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the current user's profile.

    Used by the /api/v1/auth/me/ endpoint.
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "full_name",
            "first_name",
            "last_name",
            "organisation",
            "country",
            "timezone",
            "role",
            "is_staff",
            "created_at",
        ]
        read_only_fields = fields

    def get_full_name(self, obj: User) -> str:
        """Return the user's full name."""
        return obj.get_full_name()
