"""
AstronomicalEvent model — a confirmed astronomical event detected by the network.

Design decisions:
- code is the canonical public identifier assigned by the admin (e.g. "SE-2026-001").
  It is unique, immutable in practice, and used in publications and citizen reports.
- event_type mirrors the choices in notices.EventType so that public reports can be
  cross-referenced, but this model represents the *confirmed* record.
- detected_at stores the UTC datetime of the observed event (not the record creation).
- duration_ms and peak_magnitude are scientific measurements — nullable since they
  may not always be obtainable (radio-only detection, partial data, etc.).
- stations / cameras / radio_receivers are plain M2M (no through model) because the
  association itself is the fact; per-detection metadata (signal strength, frame
  count, etc.) can be added in a future phase via explicit through models.
- status drives visibility: only "published" events are shown publicly.
- created_by is the admin user who created the record.

@file   sky_events/apps/events/models.py
@author slopez.tech
"""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from sky_events.apps.camera.models import Camera
from sky_events.apps.core.models import TimeStampedModel
from sky_events.apps.radio.models import RadioReceiver
from sky_events.apps.station.models import Station


class EventType(models.TextChoices):
    METEOR = "meteor", _("Meteor")
    FIREBALL = "fireball", _("Fireball / bolide")
    AURORA = "aurora", _("Aurora")
    SATELLITE = "satellite", _("Satellite / re-entry")
    SPORADIC = "sporadic", _("Sporadic")
    SHOWER = "shower", _("Meteor shower")
    OTHER = "other", _("Other")


class EventStatus(models.TextChoices):
    UNCONFIRMED = "unconfirmed", _("Unconfirmed")
    CONFIRMED = "confirmed", _("Confirmed")
    PUBLISHED = "published", _("Published")
    ARCHIVED = "archived", _("Archived")


class AstronomicalEvent(TimeStampedModel):
    """
    A confirmed astronomical event detected by one or more network stations.

    The admin creates the event, assigns a unique code, fills in scientific
    measurements, and links all contributing stations, cameras and radios.
    """

    # --- Identity -------------------------------------------------------
    code = models.CharField(
        _("event code"),
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Unique admin-assigned identifier, e.g. SE-2026-001."),
    )
    name = models.CharField(
        _("name"),
        max_length=255,
        help_text=_("Short human-readable name for the event."),
    )
    event_type = models.CharField(
        _("event type"),
        max_length=20,
        choices=EventType.choices,
        default=EventType.METEOR,
        db_index=True,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.UNCONFIRMED,
        db_index=True,
    )

    # --- Timing ---------------------------------------------------------
    detected_at = models.DateTimeField(
        _("detected at"),
        db_index=True,
        help_text=_("UTC datetime when the event was observed."),
    )
    duration_ms = models.PositiveIntegerField(
        _("duration (ms)"),
        null=True,
        blank=True,
        help_text=_("Observed duration of the event in milliseconds."),
    )

    # --- Scientific measurements ----------------------------------------
    peak_magnitude = models.DecimalField(
        _("peak magnitude"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Peak apparent magnitude (negative = brighter)."),
    )
    altitude_km = models.DecimalField(
        _("altitude (km)"),
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Estimated ablation altitude above sea level in km."),
    )
    velocity_km_s = models.DecimalField(
        _("velocity (km/s)"),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Estimated geocentric entry velocity in km/s."),
    )

    # --- Narrative ------------------------------------------------------
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Public description of the event."),
    )
    notes = models.TextField(
        _("internal notes"),
        blank=True,
        help_text=_("Admin-only notes (not shown publicly)."),
    )

    # --- Detections (M2M) -----------------------------------------------
    stations = models.ManyToManyField(
        Station,
        blank=True,
        related_name="events",
        verbose_name=_("stations"),
        help_text=_("Stations that detected this event."),
    )
    cameras = models.ManyToManyField(
        Camera,
        blank=True,
        related_name="events",
        verbose_name=_("cameras"),
        help_text=_("Cameras that recorded this event."),
    )
    radio_receivers = models.ManyToManyField(
        RadioReceiver,
        blank=True,
        related_name="events",
        verbose_name=_("radio receivers"),
        help_text=_("Radio receivers that detected an echo for this event."),
    )

    # --- Authorship ------------------------------------------------------
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_events",
        verbose_name=_("created by"),
    )

    class Meta:
        verbose_name = _("astronomical event")
        verbose_name_plural = _("astronomical events")
        ordering = ["-detected_at"]

    def __str__(self) -> str:
        return f"[{self.code}] {self.name}"

    @property
    def is_published(self) -> bool:
        return self.status == EventStatus.PUBLISHED
