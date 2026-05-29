"""
Custom UserManager for SkyEvents.

Uses email as the primary identifier instead of username.

@file   sky_events/apps/users/managers.py
@author slopez.tech
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.base_user import BaseUserManager

if TYPE_CHECKING:
    from sky_events.apps.users.models import User


class UserManager(BaseUserManager["User"]):
    """
    Custom manager for the User model.

    Creates users with email as the login field.
    Enforces that superusers have is_staff=True and is_superuser=True.
    """

    def create_user(
        self,
        email: str,
        username: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        """
        Create and save a regular user.

        @param  email           User's email address (used for login).
        @param  username        User's display username.
        @param  password        Plaintext password (will be hashed).
        @param  extra_fields    Additional model fields.
        @return The created User instance.
        @raises ValueError if email or username is empty.
        """
        if not email:
            raise ValueError("Users must have an email address.")
        if not username:
            raise ValueError("Users must have a username.")

        email = self.normalize_email(email)
        user: "User" = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        username: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        """
        Create and save a superuser with all permissions.

        @param  email           User's email address.
        @param  username        User's display username.
        @param  password        Plaintext password.
        @param  extra_fields    Additional model fields.
        @return The created superuser instance.
        @raises ValueError if is_staff or is_superuser are not True.
        """
        from sky_events.apps.users.models import UserRole  # noqa: PLC0415

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", UserRole.ADMIN)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)
