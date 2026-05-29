"""
Admin configuration for the events app.

@file   sky_events/apps/events/admin.py
@author slopez.tech
"""

from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from sky_events.apps.notices.models import EventNotice, NoticeStatus

from .models import AstronomicalEvent, EventStatus


class EventNoticeInline(admin.TabularInline):
    model = EventNotice
    fk_name = "event"
    fields = ["name", "email", "event_type", "observation_date", "status"]
    readonly_fields = ["name", "email", "event_type", "observation_date"]
    extra = 0
    can_delete = False
    verbose_name = _("Linked notice")
    verbose_name_plural = _("Linked notices")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AstronomicalEvent)
class AstronomicalEventAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "event_type",
        "detected_at",
        "status",
        "station_count",
        "camera_count",
        "radio_count",
        "created_by",
    ]
    list_filter = ["status", "event_type", "detected_at"]
    search_fields = ["code", "name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-detected_at"]
    date_hierarchy = "detected_at"
    filter_horizontal = ["stations", "cameras", "radio_receivers"]
    inlines = [EventNoticeInline]

    fieldsets = [
        (
            _("Identity"),
            {"fields": ["code", "name", "event_type", "status"]},
        ),
        (
            _("Timing"),
            {"fields": ["detected_at", "duration_ms"]},
        ),
        (
            _("Measurements"),
            {
                "fields": ["peak_magnitude", "altitude_km", "velocity_km_s"],
                "classes": ["collapse"],
            },
        ),
        (
            _("Detections"),
            {"fields": ["stations", "cameras", "radio_receivers"]},
        ),
        (
            _("Description"),
            {"fields": ["description", "notes"]},
        ),
        (
            _("Metadata"),
            {
                "fields": ["created_by", "created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description=_("Stations"))
    def station_count(self, obj):
        return obj.stations.count()

    @admin.display(description=_("Cameras"))
    def camera_count(self, obj):
        return obj.cameras.count()

    @admin.display(description=_("Radios"))
    def radio_count(self, obj):
        return obj.radio_receivers.count()

    @admin.action(description=_("Publish selected events"))
    def publish(self, request, queryset):
        queryset.update(status=EventStatus.PUBLISHED)

    @admin.action(description=_("Mark selected as confirmed"))
    def confirm(self, request, queryset):
        queryset.update(status=EventStatus.CONFIRMED)

    @admin.action(description=_("Archive selected events"))
    def archive(self, request, queryset):
        queryset.update(status=EventStatus.ARCHIVED)

    actions = [publish, confirm, archive]
