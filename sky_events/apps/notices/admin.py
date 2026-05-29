"""
Admin configuration for the notices app.

@file   sky_events/apps/notices/admin.py
@author slopez.tech
"""

from __future__ import annotations

from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import EventNotice, NoticeStatus


@admin.register(EventNotice)
class EventNoticeAdmin(admin.ModelAdmin):
    list_display = ["__str__", "email", "status", "event", "created_at"]
    list_filter = ["status", "event_type", "event"]
    search_fields = ["name", "email", "location", "description"]
    readonly_fields = ["created_at", "updated_at", "reviewed_by", "reviewed_at"]
    raw_id_fields = ["event"]
    ordering = ["-created_at"]

    @admin.action(description=_("Mark selected as approved"))
    def approve(self, request, queryset):
        queryset.update(
            status=NoticeStatus.APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )

    @admin.action(description=_("Mark selected as rejected"))
    def reject(self, request, queryset):
        queryset.update(
            status=NoticeStatus.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )

    actions = [approve, reject]
