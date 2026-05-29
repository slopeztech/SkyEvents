"""
Django admin registration for the reports app.

@file   sky_events/apps/reports/admin.py
@author slopez.tech
"""

from __future__ import annotations

from django.contrib import admin

from .models import ReportFile, StationReport


class ReportFileInline(admin.TabularInline):
    model = ReportFile
    extra = 1
    fields = ("file_type", "filename", "file_size_bytes", "description", "is_available")


@admin.register(StationReport)
class StationReportAdmin(admin.ModelAdmin):
    list_display = ("station", "camera", "radio_receiver", "recorded_at", "status", "event")
    list_filter = ("status", "station")
    search_fields = ("station__name", "camera__name", "radio_receiver__name", "notes")
    raw_id_fields = ("event",)
    date_hierarchy = "recorded_at"
    inlines = [ReportFileInline]
