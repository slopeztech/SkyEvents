"""
Django admin registration for SiteConfig.

@file   sky_events/apps/webconfig/admin.py
@author slopez.tech
"""

from __future__ import annotations

from django.contrib import admin

from .models import SiteConfig


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Language",
            {"fields": ("language_code",)},
        ),
        (
            "Site identity",
            {"fields": ("site_name", "page_title")},
        ),
        (
            "Hero section",
            {
                "fields": (
                    "hero_badge",
                    "hero_pre_highlight",
                    "hero_highlight",
                    "hero_post_highlight",
                    "hero_subtitle",
                    "hero_bg_style",
                )
            },
        ),
        (
            "Stats bar",
            {
                "fields": (
                    "stats_stations_label",
                    "stats_cameras_label",
                    "stats_radios_label",
                    "stats_events_label",
                )
            },
        ),
        (
            "CTA section",
            {"fields": ("cta_title", "cta_subtitle")},
        ),
        (
            "Contact / Footer",
            {"fields": ("contact_email", "footer_text")},
        ),
    )

    def has_add_permission(self, request):
        from django.conf import settings

        # Allow adding only if any supported language still lacks a config row
        existing = set(SiteConfig.objects.values_list("language_code", flat=True))
        supported = {code for code, _ in settings.LANGUAGES}
        return bool(supported - existing)

    def has_delete_permission(self, request, obj=None):
        return False
