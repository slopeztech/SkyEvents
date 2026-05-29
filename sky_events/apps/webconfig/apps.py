"""
AppConfig for the webconfig app.

@file   sky_events/apps/webconfig/apps.py
@author slopez.tech
"""

from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WebConfigConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sky_events.apps.webconfig"
    verbose_name = _("Web Configuration")
