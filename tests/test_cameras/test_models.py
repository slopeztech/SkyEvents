"""
Unit and integration tests for the Camera model.

@file   tests/test_cameras/test_models.py
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from sky_events.apps.camera.models import Camera
from sky_events.apps.core.models import DeviceStatus
from tests.factories import CameraFactory, StationFactory


@pytest.mark.django_db
class TestCameraModel:
    """Tests for Camera model creation and field behaviour."""

    def test_create_camera(self) -> None:
        """A Camera can be created with valid data."""
        camera = CameraFactory()
        assert camera.pk is not None

    def test_camera_str(self) -> None:
        """__str__ returns 'Name [code] @ station_code'."""
        station = StationFactory(code="mad-north")
        camera = CameraFactory(station=station, name="East cam", code="cam-east")
        assert str(camera) == "East cam [cam-east] @ mad-north"

    def test_camera_station_relationship(self) -> None:
        """Station.cameras reverse relation returns all cameras."""
        station = StationFactory()
        c1 = CameraFactory(station=station)
        c2 = CameraFactory(station=station)
        assert station.cameras.count() == 2
        assert c1 in station.cameras.all()
        assert c2 in station.cameras.all()

    def test_camera_code_unique(self) -> None:
        """Two cameras with the same code cannot be created."""
        station = StationFactory()
        CameraFactory(station=station, code="cam-unique")
        with pytest.raises(IntegrityError):
            Camera.objects.create(
                station=station,
                name="Duplicate",
                code="cam-unique",
            )

    def test_camera_default_status_active(self) -> None:
        """Default status is ACTIVE."""
        camera = CameraFactory()
        assert camera.status == DeviceStatus.ACTIVE
        assert camera.is_active is True

    def test_camera_resolution_property(self) -> None:
        """resolution property returns formatted WxH string."""
        camera = CameraFactory(resolution_width=1920, resolution_height=1080)
        assert camera.resolution == "1920\u00d71080"

    def test_camera_resolution_property_none_when_missing(self) -> None:
        """resolution property returns None when dimensions are not set."""
        camera = CameraFactory(resolution_width=None, resolution_height=None)
        assert camera.resolution is None

    def test_camera_elevation_validation(self) -> None:
        """elevation_deg validator rejects values outside [-90, 90]."""
        camera = CameraFactory.build(elevation_deg=Decimal("91.0"))
        with pytest.raises(ValidationError):
            camera.full_clean()

    def test_camera_azimuth_validation(self) -> None:
        """azimuth_deg validator rejects values outside [0, 360]."""
        camera = CameraFactory.build(azimuth_deg=Decimal("-1.0"))
        with pytest.raises(ValidationError):
            camera.full_clean()

    def test_camera_technical_params_default_empty_dict(self) -> None:
        """technical_params defaults to an empty dict."""
        camera = CameraFactory()
        assert camera.technical_params == {}

    def test_camera_cascade_delete_on_station_delete(self) -> None:
        """Deleting a station cascades to its cameras."""
        station = StationFactory()
        cam_id = CameraFactory(station=station).pk
        station.delete()
        assert not Camera.objects.filter(pk=cam_id).exists()
