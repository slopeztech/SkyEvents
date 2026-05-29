"""
Django admin configuration for the cameras app.

@file   sky_events/apps/camera/admin.py
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from sky_events.apps.camera.models import Camera


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    """Admin view for Camera model."""

    # --- List view ---
    list_display = (
        "name",
        "code",
        "station",
        "camera_type",
        "status",
        "model_name",
        "resolution",
        "fps",
        "azimuth_deg",
        "elevation_deg",
        "installed_at",
    )
    list_filter = ("status", "camera_type", "station__status", "sensor_type")
    search_fields = (
        "name",
        "code",
        "model_name",
        "station__name",
        "station__code",
    )
    ordering = ("station__name", "name")
    list_select_related = ("station", "station__owner")

    # --- Detail view ---
    readonly_fields = ("id", "created_at", "updated_at", "resolution")
    fieldsets = (
        (
            None,
            {
                "fields": ("id", "station", "name", "code", "camera_type", "status"),
            },
        ),
        (
            _("Hardware"),
            {
                "fields": (
                    "model_name",
                    "sensor_type",
                    "resolution_width",
                    "resolution_height",
                    "fps",
                    "lens_mm",
                ),
            },
        ),
        (
            _("Pointing geometry"),
            {
                "description": _("Azimuth and elevation are required for Fixed cameras."),
                "fields": ("field_of_view_deg", "azimuth_deg", "elevation_deg"),
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
