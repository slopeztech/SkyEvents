"""
Notices app — public event reports.

Allows unauthenticated visitors to submit sightings or reports of
astronomical events (meteors, fireballs, auroras…).
Admins can review and classify submissions from the admin dashboard.

@file   sky_events/apps/notices/apps.py
@author slopez.tech
"""

from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NoticesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sky_events.apps.notices"
    verbose_name = _("Notices")
