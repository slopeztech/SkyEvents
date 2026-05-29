"""
API views for the station-script endpoints.

All views require JWT authentication AND a matching X-Script-Token header
(enforced by ScriptTokenPermission).  Requests are throttled using the
"station" scope (10 000 req/hour per user).

Endpoints
---------
POST   /api/v1/station/reports/
    Create a StationReport (with optional ReportFile metadata records).

GET    /api/v1/station/requirements/
    List pending MediaRequirements for the authenticated user's stations.

POST   /api/v1/station/requirements/{pk}/media/
    Upload a file to fulfil a MediaRequirement.

@file   sky_events/apps/reports/api/views.py
@author slopez.tech
"""

from __future__ import annotations

from django.db import models as db_models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from sky_events.apps.camera.models import Camera
from sky_events.apps.core.api.permissions import ScriptTokenPermission
from sky_events.apps.core.api.throttles import StationThrottle
from sky_events.apps.radio.models import RadioReceiver
from sky_events.apps.reports.models import (
    MediaRequirement,
    ReportAttachment,
    ReportFile,
    RequirementStatus,
    StationReport,
)
from sky_events.apps.station.models import Station

from .serializers import (
    MediaRequirementSerializer,
    ReportAttachmentSerializer,
    StationReportCreateSerializer,
)


class StationReportCreateAPIView(CreateAPIView):
    """
    POST /api/v1/station/reports/

    Create a detection report produced by a station device.

    The station is identified by ``station_hash_id`` and must belong to
    the authenticated user.  Devices (camera / radio) are looked up by
    their ``hash_id``; if not found they are silently omitted so that the
    report is still accepted.

    Returns the new report's ``id`` and initial ``status``.
    """

    permission_classes = [ScriptTokenPermission]
    throttle_classes = [StationThrottle]
    serializer_class = StationReportCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Verify that the station belongs to the authenticated user.
        station = Station.objects.filter(
            hash_id=data["station_hash_id"],
            owner=request.user,
        ).first()
        if station is None:
            raise PermissionDenied(
                _("Station not found or not owned by the authenticated user.")
            )

        # Resolve optional camera (must belong to the same station).
        camera: Camera | None = None
        if data.get("camera_hash_id"):
            camera = Camera.objects.filter(
                hash_id=data["camera_hash_id"],
                station=station,
            ).first()

        # Resolve optional radio receiver (must belong to the same station).
        radio: RadioReceiver | None = None
        if data.get("radio_hash_id"):
            radio = RadioReceiver.objects.filter(
                hash_id=data["radio_hash_id"],
                station=station,
            ).first()

        report = StationReport.objects.create(
            station=station,
            camera=camera,
            radio_receiver=radio,
            recorded_at=data["recorded_at"],
            duration_ms=data.get("duration_ms"),
            notes=data.get("notes", ""),
        )

        # Bulk-create file metadata records (0 DB queries if list is empty).
        files_data = data.get("files", [])
        if files_data:
            ReportFile.objects.bulk_create(
                [ReportFile(report=report, **file_item) for file_item in files_data]
            )

        return Response(
            {"id": str(report.pk), "status": report.status},
            status=status.HTTP_201_CREATED,
        )


class MediaRequirementListAPIView(ListAPIView):
    """
    GET /api/v1/station/requirements/

    Return all *pending* MediaRequirements for the authenticated user's
    stations, excluding any that have passed their ``expires_at`` deadline.
    """

    permission_classes = [ScriptTokenPermission]
    throttle_classes = [StationThrottle]
    serializer_class = MediaRequirementSerializer

    def get_queryset(self):
        now = timezone.now()
        return (
            MediaRequirement.objects.filter(
                station__owner=self.request.user,
                status=RequirementStatus.PENDING,
            )
            .filter(
                db_models.Q(expires_at__isnull=True) | db_models.Q(expires_at__gt=now)
            )
            .select_related("station")
        )


class ReportAttachmentUploadAPIView(CreateAPIView):
    """
    POST /api/v1/station/requirements/{pk}/media/

    Upload a file to fulfil a MediaRequirement.

    Accepts ``multipart/form-data`` with fields:
    - ``file``          — the actual file (required)
    - ``original_path`` — local path on the station (required)
    - ``file_type``     — one of the FileType choices (required)

    After each successful upload the view checks whether all
    ``requested_paths`` have been uploaded; if so, the requirement is
    automatically marked as ``fulfilled``.

    Returns the new attachment's ``id`` and the current requirement status.
    """

    permission_classes = [ScriptTokenPermission]
    throttle_classes = [StationThrottle]
    serializer_class = ReportAttachmentSerializer
    parser_classes = [MultiPartParser]

    def _get_requirement(self) -> MediaRequirement:
        return get_object_or_404(
            MediaRequirement,
            pk=self.kwargs["pk"],
            station__owner=self.request.user,
            status=RequirementStatus.PENDING,
        )

    def create(self, request, *args, **kwargs):
        requirement = self._get_requirement()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = request.data.get("file")
        file_size = uploaded_file.size if uploaded_file else None

        attachment: ReportAttachment = serializer.save(
            requirement=requirement,
            uploaded_by=request.user,
            file_size_bytes=file_size,
        )

        # Auto-fulfil the requirement when all requested paths are present.
        uploaded_paths = set(
            requirement.attachments.values_list("original_path", flat=True)
        )
        requested_paths = set(requirement.requested_paths)
        if requested_paths and requested_paths.issubset(uploaded_paths):
            requirement.status = RequirementStatus.FULFILLED
            requirement.save()

        return Response(
            {
                "id": str(attachment.pk),
                "requirement_status": requirement.status,
            },
            status=status.HTTP_201_CREATED,
        )
