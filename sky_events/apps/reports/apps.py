"""
Reports app — station-generated detection records.

Each StationReport represents a single detection produced by a station
device (camera or radio receiver). Reports can be linked to a confirmed
AstronomicalEvent and carry references to the available data files that
operators may request for analysis.

@file   sky_events/apps/reports/apps.py
@author slopez.tech
"""

from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sky_events.apps.reports"
    verbose_name = _("Reports")
