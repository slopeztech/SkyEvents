"""
DRF serializers for the station-script API.

@file   sky_events/apps/reports/api/serializers.py
@author slopez.tech
"""

from __future__ import annotations

from rest_framework import serializers

from sky_events.apps.reports.models import (
    FileType,
    MediaRequirement,
    ReportAttachment,
)

# ---------------------------------------------------------------------------
# Report creation serializers
# ---------------------------------------------------------------------------

_MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB


class ReportFileCreateSerializer(serializers.Serializer):
    """Metadata for a single file included with a station report."""

    file_type = serializers.ChoiceField(choices=FileType.choices)
    filename = serializers.CharField(max_length=512)
    file_size_bytes = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
    )
    description = serializers.CharField(
        max_length=255,
        required=False,
        default="",
        allow_blank=True,
    )


class StationReportCreateSerializer(serializers.Serializer):
    """
    Input payload for POST /api/v1/station/reports/.

    The station identifies itself by ``station_hash_id`` (the opaque token
    stored in Station.hash_id).  Optional ``camera_hash_id`` /
    ``radio_hash_id`` must belong to that station; silently ignored if not
    found so the report is still accepted.
    """

    station_hash_id = serializers.CharField(max_length=24)
    camera_hash_id = serializers.CharField(
        max_length=24,
        required=False,
        allow_blank=True,
        default="",
    )
    radio_hash_id = serializers.CharField(
        max_length=24,
        required=False,
        allow_blank=True,
        default="",
    )
    recorded_at = serializers.DateTimeField()
    duration_ms = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
    )
    notes = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
    )
    files = ReportFileCreateSerializer(many=True, required=False, default=list)


# ---------------------------------------------------------------------------
# Requirements serializer
# ---------------------------------------------------------------------------


class MediaRequirementSerializer(serializers.ModelSerializer):
    """Read-only representation of a pending MediaRequirement."""

    station_code = serializers.CharField(source="station.code", read_only=True)

    class Meta:
        model = MediaRequirement
        fields = [
            "id",
            "station_code",
            "requested_paths",
            "status",
            "notes",
            "expires_at",
            "created_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Attachment upload serializer
# ---------------------------------------------------------------------------


class ReportAttachmentSerializer(serializers.ModelSerializer):
    """Input/output for POST /api/v1/station/requirements/{id}/media/."""

    class Meta:
        model = ReportAttachment
        fields = ["id", "original_path", "file_type", "file"]
        read_only_fields = ["id"]

    def validate_file(self, value):  # type: ignore[override]
        if value.size > _MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError(
                "File too large. Maximum allowed size is 500 MB."
            )
        return value
