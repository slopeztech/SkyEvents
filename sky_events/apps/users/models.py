"""
Custom user model for SkyEvents.

Design decisions:
- email as the primary login identifier (not username)
- username retained for display / mentions
- UUIDv7 primary key (from TimeStampedModel via AbstractBaseUser)
- Explicit role field (ADMIN / STATION_OWNER) — RBAC at the model level
- timezone field per user for UI display
- country / organisation for multi-tenant future expansion
- AbstractBaseUser + PermissionsMixin for full Django auth compatibility
- Custom manager using email-based create_user / create_superuser

@file   sky_events/apps/users/models.py
@author slopez.tech
"""

from __future__ import annotations

import secrets
from typing import ClassVar

import zoneinfo

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from uuid6 import uuid7


def _generate_script_token() -> str:
    """Generate a cryptographically secure unique token for script authentication."""
    return secrets.token_urlsafe(32)

from sky_events.apps.core.models import TimeStampedModel
from sky_events.apps.users.managers import UserManager

# ---------------------------------------------------------------------------
# Timezone choices — pulled from zoneinfo (stdlib, Python 3.9+)
# ---------------------------------------------------------------------------
TIMEZONE_CHOICES: list[tuple[str, str]] = sorted(
    [(tz, tz) for tz in zoneinfo.available_timezones()],
    key=lambda x: x[0],
)


class UserRole(models.TextChoices):
    """
    Application-level roles for SkyEvents users.

    These roles are intentionally coarse-grained at the model level.
    Fine-grained permissions are handled by Django's permission system
    and DRF permission classes.
    """

    ADMIN = "admin", _("Admin")
    STATION_OWNER = "station_owner", _("Station Owner")


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Custom user model for SkyEvents.

    Replaces Django's default User model with a UUID primary key,
    email-based authentication, and domain-specific fields.

    Login field: ``email``
    Display name: ``username`` or ``get_full_name()``

    @note   This model MUST be set as ``AUTH_USER_MODEL`` before the first
            migration. Changing it later requires manual database surgery.
    """

    # Override id from TimeStampedModel to use uuid7 explicitly
    # (inherited from UUIDModel, so just documenting here)

    # --- Authentication ---
    email: models.EmailField = models.EmailField(
        unique=True,
        db_index=True,
        verbose_name=_("Email address"),
        help_text=_("Primary login identifier. Must be unique."),
    )
    username: models.CharField = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name=_("Username"),
        help_text=_("Unique display name. Used in UI and mentions."),
    )

    # --- Personal information ---
    first_name: models.CharField = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("First name"),
    )
    last_name: models.CharField = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("Last name"),
    )

    # --- Organisation ---
    organisation: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Organisation"),
        help_text=_("Optional organisation or institution name."),
    )
    country: models.CharField = models.CharField(
        max_length=2,
        blank=True,
        verbose_name=_("Country"),
        help_text=_("ISO 3166-1 alpha-2 country code (e.g. 'ES', 'US')."),
    )

    # --- Localisation ---
    timezone: models.CharField = models.CharField(
        max_length=64,
        choices=TIMEZONE_CHOICES,
        default="UTC",
        verbose_name=_("Timezone"),
        help_text=_("User's local timezone for UI display. All data is stored in UTC."),
    )

    # --- Role ---
    role: models.CharField = models.CharField(
        max_length=32,
        choices=UserRole.choices,
        default=UserRole.STATION_OWNER,
        db_index=True,
        verbose_name=_("Role"),
        help_text=_("Application role determining access level."),
    )

    # --- Django admin / staff flags ---
    is_staff: models.BooleanField = models.BooleanField(
        default=False,
        verbose_name=_("Staff status"),
        help_text=_("Designates whether the user can log into the admin site."),
    )
    is_active: models.BooleanField = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Active"),
        help_text=_(
            "Designates whether this user account should be treated as active. "
            "Deactivate instead of deleting accounts."
        ),
    )

    # --- Script authentication ---
    script_token: models.CharField = models.CharField(
        max_length=64,
        unique=True,
        default=_generate_script_token,
        editable=False,
        verbose_name=_("Script token"),
        help_text=_(
            "Unique secret token that the reporting script uses to authenticate. "
            "Never share this token publicly."
        ),
    )

    # Custom manager
    objects: ClassVar[UserManager] = UserManager()  # type: ignore[assignment]

    # Django auth configuration
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["email"]
        indexes = [
            models.Index(fields=["email"], name="users_user_email_idx"),
            models.Index(fields=["role", "is_active"], name="users_user_role_active_idx"),
        ]

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        """Return the user's full name, or email if name is not set."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self) -> str:
        """Return the user's first name, or username as fallback."""
        return self.first_name or self.username

    @property
    def is_admin(self) -> bool:
        """Return True if this user has the ADMIN role."""
        return self.role == UserRole.ADMIN

    @property
    def is_station_owner(self) -> bool:
        """Return True if this user has the STATION_OWNER role."""
        return self.role == UserRole.STATION_OWNER
