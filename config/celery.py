"""
Celery application entry point for SkyEvents.

The Celery app is created here and imported by Django via the
``CELERY_APP`` setting. All tasks are auto-discovered from installed apps.

Usage:
    celery -A config.celery worker -l info
    celery -A config.celery beat -l info
    celery -A config.celery flower  (monitoring UI)

@file   config/celery.py
@author slopez.tech
"""

from __future__ import annotations

import os

from celery import Celery
from celery.signals import setup_logging

# Set the default Django settings module for the Celery worker process
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("skyevents")

# Load Celery configuration from Django settings (CELERY_* prefix)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@setup_logging.connect
def config_loggers(*args: object, **kwargs: object) -> None:
    """
    Use Django's logging configuration for Celery workers.

    Without this, Celery would override the logging setup configured
    in Django's LOGGING setting with its own default configuration.
    """
    from logging.config import dictConfig  # noqa: PLC0415

    from django.conf import settings  # noqa: PLC0415

    dictConfig(settings.LOGGING)


@app.task(bind=True, ignore_result=True)
def debug_task(self: object) -> None:  # type: ignore[type-arg]
    """
    Debug task for verifying Celery is working correctly.

    Usage: ``from config.celery import debug_task; debug_task.delay()``
    """
    print(f"Request: {self.request!r}")  # noqa: T201
