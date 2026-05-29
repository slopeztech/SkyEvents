"""
Core application — shared infrastructure for all SkyEvents apps.

Provides:
- Abstract base models (UUIDModel, TimeStampedModel, AuditedModel)
- Custom pagination classes
- Custom exception handler
- Health check views
- Common utilities

@file   sky_events/apps/core/__init__.py
@author slopez.tech
"""

default_app_config = "sky_events.apps.core.apps.CoreConfig"
