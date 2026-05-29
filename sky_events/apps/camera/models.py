"""
Camera model — an optical all-sky or wide-angle camera attached to a station.

Design decisions:
- code is a globally unique device identifier (e.g. manufacturer serial number
  or a self-assigned slug). Used in log correlation and event attribution.
- Pointing geometry stored as (azimuth, elevation) in degrees — standard for
  meteor observation networks (IMO, FRIPON, etc.).
- resolution_width / resolution_height nullable: useful when the device is
  registered before full specs are available.
- technical_params JSONField holds SDR/camera-specific parameters not worth
  promoting to first-class columns (gain, gamma, shutter speed, …).
- installed_at is a plain Date (no time component) — the exact install time
  is not relevant and avoids timezone ambiguity.

@file   sky_events/apps/camera/models.py
@author slopez.tech
"""

from __future__ import annotations

import secrets

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from sky_events.apps.core.models import DeviceStatus, TimeStampedModel
from sky_events.apps.station.models import Station


def _generate_hash_id() -> str:
    """Generate a short cryptographically unique identifier for device config files."""
    return secrets.token_hex(12)  # 24-char hex string


class CameraType(models.TextChoices):
    """Type of camera mounting / coverage."""

    FIXED = "fixed", _("Fixed")
    ALLSKY = "allsky", _("All-sky")
    WIDE = "wide", _("Wide-angle")


class Camera(TimeStampedModel):
    """
    An optical camera installed at an observation station.

    Captures images or video of the sky for meteor/fireball/flash detection.
    One station may have multiple cameras pointing in different directions.
    """

    station: models.ForeignKey = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="cameras",
        verbose_name=_("Station"),
        help_text=_("Station this camera belongs to."),
    )

    # --- Identity ---
    name: models.CharField = models.CharField(
        max_length=255,
        verbose_name=_("Name"),
        help_text=_("Human-readable name for this camera."),
    )
    code: models.CharField = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_("Unique device identifier for this camera."),
    )
    hash_id: models.CharField = models.CharField(
        max_length=32,
        unique=True,
        default=_generate_hash_id,
        editable=False,
        verbose_name=_("Hash ID"),
        help_text=_("Short unique identifier used in script configuration files."),
    )
    camera_type: models.CharField = models.CharField(
        max_length=16,
        choices=CameraType.choices,
        default=CameraType.FIXED,
        db_index=True,
        verbose_name=_("Camera type"),
        help_text=_(
            "Type of camera: 'Fixed' points to a specific direction (azimuth/elevation required), "
            "'All-sky' covers the full dome (180 °), 'Wide-angle' covers a broad area without full coverage."
        ),
    )

    # --- Hardware specs ---
    model_name: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Camera model"),
        help_text=_("Manufacturer and model name of the camera."),
    )
    sensor_type: models.CharField = models.CharField(
        max_length=128,
        blank=True,
        verbose_name=_("Sensor type"),
        help_text=_("Image sensor type (e.g. CMOS, CCD)."),
    )
    resolution_width: models.PositiveIntegerField = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Resolution width (px)"),
        help_text=_("Horizontal resolution in pixels."),
    )
    resolution_height: models.PositiveIntegerField = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Resolution height (px)"),
        help_text=_("Vertical resolution in pixels."),
    )
    fps: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Frame rate (fps)"),
        help_text=_("Recording frame rate in frames per second."),
    )

    # --- Optical specs ---
    field_of_view_deg: models.DecimalField = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(360)],
        verbose_name=_("Field of view (°)"),
        help_text=_("Diagonal field of view in degrees."),
    )
    lens_mm: models.DecimalField = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("Focal length (mm)"),
        help_text=_("Camera lens focal length in millimetres."),
    )

    # --- Pointing geometry ---
    azimuth_deg: models.DecimalField = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(360)],
        verbose_name=_("Azimuth (°)"),
        help_text=_("Azimuth pointing direction in degrees (0 = North, clockwise)."),
    )
    elevation_deg: models.DecimalField = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        verbose_name=_("Elevation (°)"),
        help_text=_("Elevation angle in degrees (0 = horizon, 90 = zenith)."),
    )

    # --- Status & lifecycle ---
    status: models.CharField = models.CharField(
        max_length=16,
        choices=DeviceStatus.choices,
        default=DeviceStatus.ACTIVE,
        db_index=True,
        verbose_name=_("Status"),
    )
    installed_at: models.DateField = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Installation date"),
        help_text=_("Date the camera was installed at the station."),
    )

    # --- Extra data ---
    technical_params: models.JSONField = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Technical parameters"),
        help_text=_("Additional technical parameters as key-value pairs."),
    )

    class Meta:
        verbose_name = _("Camera")
        verbose_name_plural = _("Cameras")
        ordering = ["station", "name"]
        indexes = [
            models.Index(fields=["station", "status"], name="camera_station_status_idx"),
            models.Index(fields=["status"], name="camera_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.code}] @ {self.station.code}"

    def save(self, *args, **kwargs) -> None:
        if self._state.adding:
            while Camera.objects.filter(hash_id=self.hash_id).exists():
                self.hash_id = _generate_hash_id()
        super().save(*args, **kwargs)

    @property
    def resolution(self) -> str | None:
        """Return formatted resolution string, e.g. '1920×1080'."""
        if self.resolution_width and self.resolution_height:
            return f"{self.resolution_width}\u00d7{self.resolution_height}"
        return None

    @property
    def is_active(self) -> bool:
        """Return True if the camera is currently operational."""
        return self.status == DeviceStatus.ACTIVE
