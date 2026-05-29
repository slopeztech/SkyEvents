"""
Events app — confirmed astronomical events detected by the network.

Admins create events, assign a unique code, and link the stations,
cameras and radio receivers that contributed to the detection.

@file   sky_events/apps/events/apps.py
@author slopez.tech
"""

from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sky_events.apps.events"
    verbose_name = _("Events")
