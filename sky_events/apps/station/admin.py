"""
Django admin configuration for the stations app.

Includes CameraInline and RadioReceiverInline so operators can manage
all devices attached to a station from a single admin page.

@file   sky_events/apps/station/admin.py
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from sky_events.apps.camera.models import Camera
from sky_events.apps.radio.models import RadioReceiver
from sky_events.apps.station.models import Station


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------


class CameraInline(admin.TabularInline):
    """Inline listing of cameras attached to a station."""

    model = Camera
    extra = 0
    fields = ("name", "code", "status", "field_of_view_deg", "azimuth_deg", "elevation_deg")
    readonly_fields = ("created_at",)
    show_change_link = True
    verbose_name = _("Camera")
    verbose_name_plural = _("Cameras")


class RadioReceiverInline(admin.TabularInline):
    """Inline listing of radio receivers attached to a station."""

    model = RadioReceiver
    extra = 0
    fields = ("name", "code", "status", "frequency_mhz", "bandwidth_khz")
    readonly_fields = ("created_at",)
    show_change_link = True
    verbose_name = _("Radio receiver")
    verbose_name_plural = _("Radio receivers")


# ---------------------------------------------------------------------------
# Station admin
# ---------------------------------------------------------------------------


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    """Admin view for Station model."""

    # --- List view ---
    list_display = (
        "name",
        "code",
        "owner",
        "status",
        "latitude",
        "longitude",
        "altitude_m",
        "created_at",
    )
    list_filter = ("status", "owner")
    search_fields = ("name", "code", "owner__email", "owner__username", "description")
    ordering = ("name",)
    list_select_related = ("owner",)

    # --- Detail view ---
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": ("id", "owner", "name", "code", "description", "status"),
            },
        ),
        (
            _("Location"),
            {
                "fields": ("latitude", "longitude", "altitude_m", "timezone"),
            },
        ),
        (
            _("Metadata"),
            {
                "fields": ("metadata",),
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

    inlines = [CameraInline, RadioReceiverInline]
