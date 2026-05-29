"""
AppConfig for the core application.

@file   sky_events/apps/core/apps.py
@author slopez.tech
"""

from __future__ import annotations

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the core application."""

    name = "sky_events.apps.core"
    label = "core"
    verbose_name = "Core"

    def ready(self) -> None:
        """Perform app initialisation when Django starts."""
        # Configure structlog
        from sky_events.apps.core import logging as core_logging  # noqa: PLC0415

        core_logging.configure_structlog()
