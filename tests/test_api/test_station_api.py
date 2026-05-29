"""
Tests for the station-script REST API (v1).

Covers:
- Authentication: JWT required, X-Script-Token required
- POST /api/v1/station/reports/      — create report with and without files
- GET  /api/v1/station/requirements/ — list pending requirements
- POST /api/v1/station/requirements/{pk}/media/ — upload file

@file   tests/test_api/test_station_api.py
@author slopez.tech
"""

from __future__ import annotations

import io
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from sky_events.apps.reports.models import (
    MediaRequirement,
    ReportAttachment,
    RequirementStatus,
    StationReport,
)
from tests.factories import StationFactory, StationOwnerFactory


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _jwt_client(user) -> APIClient:
    """Return an APIClient with a valid JWT for *user*."""
    client = APIClient()
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def _station_client(user) -> APIClient:
    """Return a client authenticated with JWT + X-Script-Token."""
    client = _jwt_client(user)
    client.credentials(
        HTTP_AUTHORIZATION=client._credentials["HTTP_AUTHORIZATION"],
        HTTP_X_SCRIPT_TOKEN=user.script_token,
    )
    return client


@pytest.fixture
def owner(db):
    return StationOwnerFactory()


@pytest.fixture
def station(owner):
    return StationFactory(owner=owner)


@pytest.fixture
def other_owner(db):
    return StationOwnerFactory()


@pytest.fixture
def other_station(other_owner):
    return StationFactory(owner=other_owner)


@pytest.fixture
def pending_requirement(station):
    return MediaRequirement.objects.create(
        station=station,
        requested_paths=["/data/2024/video.mp4", "/data/2024/spectrogram.png"],
        status=RequirementStatus.PENDING,
        notes="Please upload these detection files.",
    )


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

REPORT_URL = "/api/v1/station/reports/"
REQUIREMENTS_URL = "/api/v1/station/requirements/"


def media_url(requirement_pk: str) -> str:
    return f"/api/v1/station/requirements/{requirement_pk}/media/"


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStationApiAuthentication:
    """Verify that both JWT and X-Script-Token are required on every endpoint."""

    def test_unauthenticated_report_rejected(self, station):
        client = APIClient()
        resp = client.post(REPORT_URL, {}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jwt_only_report_rejected(self, owner, station):
        """JWT without X-Script-Token must be rejected."""
        client = _jwt_client(owner)
        resp = client.post(
            REPORT_URL,
            {"station_hash_id": station.hash_id, "recorded_at": "2024-01-01T00:00:00Z"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_wrong_script_token_rejected(self, owner, station):
        client = _jwt_client(owner)
        client.credentials(
            HTTP_AUTHORIZATION=client._credentials["HTTP_AUTHORIZATION"],
            HTTP_X_SCRIPT_TOKEN="wrong-token-value",
        )
        resp = client.post(
            REPORT_URL,
            {"station_hash_id": station.hash_id, "recorded_at": "2024-01-01T00:00:00Z"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_requirements_rejected(self):
        client = APIClient()
        resp = client.get(REQUIREMENTS_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jwt_only_requirements_rejected(self, owner):
        client = _jwt_client(owner)
        resp = client.get(REQUIREMENTS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Report creation tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateReport:
    """POST /api/v1/station/reports/"""

    def test_create_minimal_report(self, owner, station):
        client = _station_client(owner)
        payload = {
            "station_hash_id": station.hash_id,
            "recorded_at": "2024-08-15T22:30:00Z",
        }
        resp = client.post(REPORT_URL, payload, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        assert "id" in resp.data
        assert resp.data["status"] == "pending"
        assert StationReport.objects.filter(pk=resp.data["id"]).exists()

    def test_create_report_with_files(self, owner, station):
        client = _station_client(owner)
        payload = {
            "station_hash_id": station.hash_id,
            "recorded_at": "2024-08-15T22:30:00Z",
            "duration_ms": 1500,
            "notes": "Bright fireball",
            "files": [
                {"file_type": "video", "filename": "/data/event.mp4", "file_size_bytes": 104857600},
                {"file_type": "spectrogram", "filename": "/data/event_spec.png"},
            ],
        }
        resp = client.post(REPORT_URL, payload, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        report = StationReport.objects.get(pk=resp.data["id"])
        assert report.files.count() == 2

    def test_station_not_owned_by_user_rejected(self, owner, other_station):
        client = _station_client(owner)
        payload = {
            "station_hash_id": other_station.hash_id,
            "recorded_at": "2024-08-15T22:30:00Z",
        }
        resp = client.post(REPORT_URL, payload, format="json")

        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_required_fields_rejected(self, owner, station):
        client = _station_client(owner)
        # Missing recorded_at
        resp = client.post(
            REPORT_URL,
            {"station_hash_id": station.hash_id},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "recorded_at" in resp.data.get("errors", resp.data)

    def test_unknown_station_hash_rejected(self, owner):
        client = _station_client(owner)
        resp = client.post(
            REPORT_URL,
            {"station_hash_id": "nonexistent000", "recorded_at": "2024-01-01T00:00:00Z"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Requirements listing tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListRequirements:
    """GET /api/v1/station/requirements/"""

    def test_returns_only_pending_for_own_stations(
        self, owner, station, other_station
    ):
        # Pending for own station — should appear
        own_req = MediaRequirement.objects.create(
            station=station,
            requested_paths=["/data/file.mp4"],
            status=RequirementStatus.PENDING,
        )
        # Fulfilled for own station — must NOT appear
        MediaRequirement.objects.create(
            station=station,
            requested_paths=["/data/other.mp4"],
            status=RequirementStatus.FULFILLED,
        )
        # Pending for other owner's station — must NOT appear
        MediaRequirement.objects.create(
            station=other_station,
            requested_paths=["/data/secret.mp4"],
            status=RequirementStatus.PENDING,
        )

        client = _station_client(owner)
        resp = client.get(REQUIREMENTS_URL)

        assert resp.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in resp.data["results"] if "results" in resp.data] or [
            item["id"] for item in resp.data
        ]
        assert str(own_req.pk) in ids
        assert len(ids) == 1

    def test_expired_requirement_excluded(self, owner, station):
        past = timezone.now() - timedelta(hours=1)
        MediaRequirement.objects.create(
            station=station,
            requested_paths=["/data/file.mp4"],
            status=RequirementStatus.PENDING,
            expires_at=past,
        )

        client = _station_client(owner)
        resp = client.get(REQUIREMENTS_URL)

        assert resp.status_code == status.HTTP_200_OK
        data = resp.data.get("results", resp.data)
        assert len(data) == 0

    def test_not_expired_requirement_included(self, owner, station):
        future = timezone.now() + timedelta(hours=1)
        req = MediaRequirement.objects.create(
            station=station,
            requested_paths=["/data/file.mp4"],
            status=RequirementStatus.PENDING,
            expires_at=future,
        )

        client = _station_client(owner)
        resp = client.get(REQUIREMENTS_URL)

        data = resp.data.get("results", resp.data)
        ids = [item["id"] for item in data]
        assert str(req.pk) in ids


# ---------------------------------------------------------------------------
# Media upload tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUploadMedia:
    """POST /api/v1/station/requirements/{pk}/media/"""

    def _fake_file(self, name: str = "video.mp4", content: bytes = b"fake-video-data") -> io.BytesIO:
        buf = io.BytesIO(content)
        buf.name = name
        return buf

    def test_upload_file_succeeds(self, owner, pending_requirement):
        client = _station_client(owner)
        url = media_url(pending_requirement.pk)
        resp = client.post(
            url,
            {
                "file": self._fake_file(),
                "original_path": "/data/2024/video.mp4",
                "file_type": "video",
            },
            format="multipart",
        )

        assert resp.status_code == status.HTTP_201_CREATED
        assert "id" in resp.data
        assert ReportAttachment.objects.filter(pk=resp.data["id"]).exists()

    def test_auto_fulfill_when_all_paths_uploaded(self, owner, pending_requirement):
        client = _station_client(owner)
        url = media_url(pending_requirement.pk)

        # Upload first file
        client.post(
            url,
            {
                "file": self._fake_file("video.mp4"),
                "original_path": "/data/2024/video.mp4",
                "file_type": "video",
            },
            format="multipart",
        )

        # Upload second file — should trigger auto-fulfil
        resp = client.post(
            url,
            {
                "file": self._fake_file("spectrogram.png", b"fake-png"),
                "original_path": "/data/2024/spectrogram.png",
                "file_type": "spectrogram",
            },
            format="multipart",
        )

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["requirement_status"] == RequirementStatus.FULFILLED
        pending_requirement.refresh_from_db()
        assert pending_requirement.status == RequirementStatus.FULFILLED

    def test_cannot_upload_to_other_owners_requirement(
        self, other_owner, pending_requirement
    ):
        client = _station_client(other_owner)
        url = media_url(pending_requirement.pk)
        resp = client.post(
            url,
            {
                "file": self._fake_file(),
                "original_path": "/data/2024/video.mp4",
                "file_type": "video",
            },
            format="multipart",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_upload_to_fulfilled_requirement(self, owner, pending_requirement):
        pending_requirement.status = RequirementStatus.FULFILLED
        pending_requirement.save()

        client = _station_client(owner)
        url = media_url(pending_requirement.pk)
        resp = client.post(
            url,
            {
                "file": self._fake_file(),
                "original_path": "/data/2024/video.mp4",
                "file_type": "video",
            },
            format="multipart",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_missing_file_field_rejected(self, owner, pending_requirement):
        client = _station_client(owner)
        url = media_url(pending_requirement.pk)
        resp = client.post(
            url,
            {"original_path": "/data/2024/video.mp4", "file_type": "video"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
