"""
Context processor that injects the SiteConfig for the active language into every template.

@file   sky_events/apps/webconfig/context_processors.py
@author slopez.tech
"""

from __future__ import annotations

from django.http import HttpRequest


def site_config(request: HttpRequest) -> dict:
    """Add ``site_config`` (language-aware) to every template context."""
    try:
        from django.conf import settings
        from django.utils.translation import get_language

        from sky_events.apps.webconfig.models import SiteConfig

        lang = get_language() or settings.LANGUAGE_CODE
        # Try the exact language code first (e.g. "es"), then the base code (e.g. "es" from "es-es")
        config = SiteConfig.objects.filter(language_code=lang).first()
        if config is None and "-" in lang:
            config = SiteConfig.objects.filter(language_code=lang.split("-")[0]).first()
        if config is None:
            # Fall back to the project default language
            config = SiteConfig.objects.filter(language_code=settings.LANGUAGE_CODE).first()
        if config is None:
            config = SiteConfig.load(settings.LANGUAGE_CODE)
    except Exception:  # pragma: no cover — table may not exist during migrations
        config = None
    return {"site_config": config}
