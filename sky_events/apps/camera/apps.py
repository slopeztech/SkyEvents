"""
AppConfig for the camera application.

@file   sky_events/apps/camera/apps.py
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CameraConfig(AppConfig):
    """Configuration for the camera app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "sky_events.apps.camera"
    verbose_name = _("Cameras")
