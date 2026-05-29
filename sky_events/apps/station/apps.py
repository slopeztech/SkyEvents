"""
AppConfig for the station application.

@file   sky_events/apps/station/apps.py
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StationConfig(AppConfig):
    """Configuration for the station app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "sky_events.apps.station"
    verbose_name = _("Stations")
