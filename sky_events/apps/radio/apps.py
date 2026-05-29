"""
AppConfig for the radio application.

@file   sky_events/apps/radio/apps.py
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RadioConfig(AppConfig):
    """Configuration for the radio app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "sky_events.apps.radio"
    verbose_name = _("Radio receivers")
