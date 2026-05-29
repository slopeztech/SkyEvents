"""
AppConfig for the users application.

@file   sky_events/apps/users/apps.py
@author slopez.tech
"""

from __future__ import annotations

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configuration for the users application."""

    name = "sky_events.apps.users"
    label = "users"
    verbose_name = "Users"
