"""
Django admin configuration for the radios app.

@file   sky_events/apps/radio/admin.py
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from sky_events.apps.radio.models import RadioReceiver


@admin.register(RadioReceiver)
class RadioReceiverAdmin(admin.ModelAdmin):
    """Admin view for RadioReceiver model."""

    # --- List view ---
    list_display = (
        "name",
        "code",
        "station",
        "status",
        "frequency_mhz",
        "bandwidth_khz",
        "receiver_model",
        "installed_at",
    )
    list_filter = ("status", "station__status", "frequency_mhz")
    search_fields = (
        "name",
        "code",
        "receiver_model",
        "station__name",
        "station__code",
    )
    ordering = ("station__name", "name")
    list_select_related = ("station", "station__owner")

    # --- Detail view ---
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": ("id", "station", "name", "code", "status"),
            },
        ),
        (
            _("RF parameters"),
            {
                "fields": ("frequency_mhz", "bandwidth_khz"),
            },
        ),
        (
            _("Hardware"),
            {
                "fields": ("receiver_model", "antenna_type", "polarization", "software"),
            },
        ),
        (
            _("Lifecycle"),
            {
                "fields": ("installed_at",),
            },
        ),
        (
            _("Technical parameters"),
            {
                "fields": ("technical_params",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
