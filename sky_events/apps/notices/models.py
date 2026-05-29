"""
EventNotice model — a public report of an astronomical event.

Unauthenticated users can submit sightings; admins review and approve them.

@file   sky_events/apps/notices/models.py
@author slopez.tech
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from sky_events.apps.core.models import TimeStampedModel


class EventType(models.TextChoices):
    METEOR = "meteor", _("Meteor")
    FIREBALL = "fireball", _("Fireball / bolide")
    AURORA = "aurora", _("Aurora")
    SATELLITE = "satellite", _("Satellite / re-entry")
    OTHER = "other", _("Other")
    UNKNOWN = "unknown", _("Unknown")


class NoticeStatus(models.TextChoices):
    PENDING = "pending", _("Pending review")
    REVIEWED = "reviewed", _("Reviewed")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")


class EventNotice(TimeStampedModel):
    """
    A public event report submitted by an unauthenticated visitor.

    Fields
    ------
    name            : Reporter's name (display only; not linked to a User).
    email           : Reporter's email for follow-up (not published).
    event_type      : Astronomical event category.
    observation_date: Local date when the event was observed.
    location        : Free-text location description (city, region, coords…).
    description     : Full narrative of the observation.
    status          : Workflow status managed by admins.
    reviewed_by     : Admin user who last changed the status.
    reviewed_at     : When the status was last changed.
    """

    name = models.CharField(_("your name"), max_length=120)
    email = models.EmailField(_("email address"))
    event_type = models.CharField(
        _("event type"),
        max_length=20,
        choices=EventType.choices,
        default=EventType.UNKNOWN,
    )
    observation_date = models.DateField(_("observation date"))
    location = models.CharField(
        _("location"),
        max_length=255,
        help_text=_("City, region, or approximate coordinates"),
    )
    description = models.TextField(
        _("description"),
        max_length=2000,
        help_text=_("Describe what you saw: direction, duration, brightness, colour…"),
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=NoticeStatus.choices,
        default=NoticeStatus.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_notices",
        verbose_name=_("reviewed by"),
    )
    reviewed_at = models.DateTimeField(_("reviewed at"), null=True, blank=True)
    event = models.ForeignKey(
        "events.AstronomicalEvent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notices",
        verbose_name=_("linked event"),
        help_text=_("Astronomical event this notice was associated to."),
    )

    class Meta:
        verbose_name = _("event notice")
        verbose_name_plural = _("event notices")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_event_type_display()} — {self.name} ({self.observation_date})"
