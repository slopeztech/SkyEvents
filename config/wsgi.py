"""
WSGI config for SkyEvents.

Exposes the WSGI callable as a module-level variable named ``application``.

@file   config/wsgi.py
@author slopez.tech
"""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_wsgi_application()
