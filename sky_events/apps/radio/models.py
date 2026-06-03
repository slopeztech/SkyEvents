"""
RadioReceiver model — a radio receiver installed at a station for meteor detection.

Design decisions:
- Radio meteor detection works by listening to forward-scatter signals from
  distant transmitters (e.g. GRAVES at 143.050 MHz, BRAMS at 49.990 MHz).
- frequency_mhz is the mandatory centre reception frequency.
- bandwidth_khz is optional; depends on the receiver's configuration.
- software stores the capture/analysis tool (SDRSharp, GQRX, Spectrum Lab…).
- installed_at is a plain Date (no time) — avoids timezone ambiguity.
- technical_params JSONField holds SDR dongle / pre-amp / filter specifics.

@file   sky_events/apps/radio/models.py
@author slopez.tech
"""

from __future__ import annotations

import secrets

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from sky_events.apps.core.models import DeviceStatus, TimeStampedModel
from sky_events.apps.station.models import Station


def _generate_hash_id() -> str:
    """Generate a short cryptographically unique identifier for device config files."""
    return secrets.token_hex(12)  # 24-char hex string


class RadioDetector(models.TextChoices):
    """Reporter detector software for this radio receiver."""

    GENERIC = "generic", _("Generic")
    ECHOES = "echoes", _("Echoes")


class RadioReceiver(TimeStampedModel):
    """
    A radio receiver installed at a station for meteor radio detection.

    Detects meteor ionisation trails by listening to forward-scatter echoes
    of a distant transmitter beacon on a set frequency.
    """

    station: models.ForeignKey = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="radio_receivers",
        verbose_name=_("Station"),
        help_text=_("Station this radio receiver belongs to."),
    )

    # --- Identity ---
    name: models.CharField = models.CharField(
        max_length=255,
        verbose_name=_("Name"),
        help_text=_("Human-readable name for this radio receiver."),
    )
    code: models.CharField = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_("Unique device identifier for this radio receiver."),
    )
    hash_id: models.CharField = models.CharField(
        max_length=32,
        unique=True,
        default=_generate_hash_id,
        editable=False,
        verbose_name=_("Hash ID"),
        help_text=_("Short unique identifier used in script configuration files."),
    )
    detector: models.CharField = models.CharField(
        max_length=32,
        choices=RadioDetector.choices,
        default=RadioDetector.GENERIC,
        verbose_name=_("Detector"),
        help_text=_("Reporter capture software used by this radio receiver."),
    )

    # --- Hardware specs ---
    receiver_model: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Receiver model"),
        help_text=_("Manufacturer and model of the radio receiver or SDR dongle."),
    )

    # --- RF parameters ---
    frequency_mhz: models.DecimalField = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        verbose_name=_("Frequency (MHz)"),
        help_text=_(
            "Reception centre frequency in megahertz (e.g. 143.050 for GRAVES)."
        ),
    )
    bandwidth_khz: models.DecimalField = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("Bandwidth (kHz)"),
        help_text=_("Reception bandwidth in kilohertz."),
    )

    # --- Antenna ---
    antenna_type: models.CharField = models.CharField(
        max_length=128,
        blank=True,
        verbose_name=_("Antenna type"),
        help_text=_(
            "Antenna type used for meteor radio detection (e.g. Yagi, dipole)."
        ),
    )
    polarization: models.CharField = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_("Polarization"),
        help_text=_(
            "Antenna polarization (e.g. horizontal, vertical, circular)."
        ),
    )

    # --- Software ---
    software: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Software"),
        help_text=_(
            "Software used for reception and recording "
            "(e.g. SDRSharp, GQRX, Spectrum Lab)."
        ),
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
        help_text=_("Date the radio receiver was installed at the station."),
    )

    # --- Extra data ---
    technical_params: models.JSONField = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Technical parameters"),
        help_text=_("Additional technical parameters as key-value pairs."),
    )

    class Meta:
        verbose_name = _("Radio receiver")
        verbose_name_plural = _("Radio receivers")
        ordering = ["station", "name"]
        indexes = [
            models.Index(fields=["station", "status"], name="radio_station_status_idx"),
            models.Index(fields=["status"], name="radio_status_idx"),
            models.Index(fields=["frequency_mhz"], name="radio_frequency_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.code}] {self.frequency_mhz} MHz @ {self.station.code}"

    def save(self, *args, **kwargs) -> None:
        if self._state.adding:
            while RadioReceiver.objects.filter(hash_id=self.hash_id).exists():
                self.hash_id = _generate_hash_id()
        super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        """Return True if the receiver is currently operational."""
        return self.status == DeviceStatus.ACTIVE
