"""
ASGI config for SkyEvents.

Exposes the ASGI callable as a module-level variable named ``application``.
Currently uses WSGI-over-ASGI — replace with channels/daphne when WebSocket
support is added in a future phase.

@file   config/asgi.py
@author slopez.tech
"""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_asgi_application()
