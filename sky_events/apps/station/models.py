"""
Station model — a physical observation station owned by a user.

Design decisions:
- A User (station owner) can own one or more Stations.
- code is a unique slug used as the machine-readable station identifier
  (also used for API key scoping in future phases).
- latitude / longitude validated at [-90,90] and [-180,180] respectively.
- altitude_m in integer metres (sufficient precision for ground stations).
- timezone stored per-station for local-time display; ALL stored timestamps
  are UTC — this field is display-only.
- metadata: open JSONField for station-specific config not modelled explicitly.
- SoftDelete NOT applied here: station deletion is rare and audited manually.

@file   sky_events/apps/station/models.py
@author slopez.tech
"""

from __future__ import annotations

import secrets
import zoneinfo
from typing import ClassVar

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from sky_events.apps.core.models import DeviceStatus, TimeStampedModel


def _generate_hash_id() -> str:
    """Generate a short cryptographically unique identifier for device config files."""
    return secrets.token_hex(12)  # 24-char hex string

# ---------------------------------------------------------------------------
# Timezone choices (stdlib, no extra dependency)
# ---------------------------------------------------------------------------
TIMEZONE_CHOICES: list[tuple[str, str]] = sorted(
    [(tz, tz) for tz in zoneinfo.available_timezones()],
    key=lambda x: x[0],
)


class Station(TimeStampedModel):
    """
    A physical automated observation station.

    Each station is owned by exactly one user and may have zero or more
    cameras and zero or more radio receivers attached.

    @note   ``code`` is the canonical machine identifier and must remain
            stable once assigned (used in API auth and log correlation).
    """

    owner: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stations",
        verbose_name=_("Owner"),
        help_text=_("User who owns and operates this station."),
    )

    # --- Identity ---
    name: models.CharField = models.CharField(
        max_length=255,
        verbose_name=_("Name"),
        help_text=_("Human-readable station name."),
    )
    code: models.SlugField = models.SlugField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_("Unique slug identifying this station (URL-safe)."),
    )
    hash_id: models.CharField = models.CharField(
        max_length=32,
        unique=True,
        default=_generate_hash_id,
        editable=False,
        verbose_name=_("Hash ID"),
        help_text=_("Short unique identifier used in script configuration files."),
    )
    description: models.TextField = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Optional free-text description of the station."),
    )

    # --- Geolocation ---
    latitude: models.DecimalField = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        verbose_name=_("Latitude"),
        help_text=_("Geographic latitude in decimal degrees. Range: −90 to +90."),
    )
    longitude: models.DecimalField = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        verbose_name=_("Longitude"),
        help_text=_("Geographic longitude in decimal degrees. Range: −180 to +180."),
    )
    altitude_m: models.IntegerField = models.IntegerField(
        verbose_name=_("Altitude (m)"),
        help_text=_("Elevation above sea level in metres."),
    )

    # --- Localisation (display only — storage is always UTC) ---
    timezone: models.CharField = models.CharField(
        max_length=64,
        choices=TIMEZONE_CHOICES,
        default="UTC",
        verbose_name=_("Local timezone"),
        help_text=_(
            "Station's physical timezone — for display only. "
            "All stored timestamps are UTC."
        ),
    )

    # --- Status ---
    status: models.CharField = models.CharField(
        max_length=16,
        choices=DeviceStatus.choices,
        default=DeviceStatus.ACTIVE,
        db_index=True,
        verbose_name=_("Status"),
    )

    # --- Extra data ---
    metadata: models.JSONField = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Metadata"),
        help_text=_("Arbitrary key-value pairs for station-specific configuration."),
    )

    class Meta:
        verbose_name = _("Station")
        verbose_name_plural = _("Stations")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["owner", "status"], name="station_owner_status_idx"),
            models.Index(fields=["status"], name="station_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.code}]"

    @property
    def is_active(self) -> bool:
        """Return True if the station is currently operational."""
        return self.status == DeviceStatus.ACTIVE
