"""
SkyEvents — Astronomical event management platform.

@package sky_events
@author  slopez.tech
"""

# Ensure the Celery app is loaded when Django starts.
# This is required so that @shared_task decorators work correctly.
from config.celery import app as celery_app  # noqa: F401

__all__ = ["celery_app"]
