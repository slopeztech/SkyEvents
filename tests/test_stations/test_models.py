"""
Unit and integration tests for the Station model.

@file   tests/test_stations/test_models.py
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from sky_events.apps.core.models import DeviceStatus
from sky_events.apps.station.models import Station
from tests.factories import StationFactory, StationOwnerFactory


@pytest.mark.django_db
class TestStationModel:
    """Tests for Station model creation and field behaviour."""

    def test_create_station(self) -> None:
        """A Station can be created with valid data."""
        station = StationFactory()
        assert station.pk is not None
        assert station.id is not None

    def test_station_str(self) -> None:
        """__str__ returns 'Name [code]'."""
        station = StationFactory(name="Madrid North", code="mad-north")
        assert str(station) == "Madrid North [mad-north]"

    def test_station_uuid_pk(self) -> None:
        """Station PK is a non-null UUID."""
        station = StationFactory()
        assert station.id is not None
        assert len(str(station.id)) == 36  # UUID canonical form

    def test_station_default_status_active(self) -> None:
        """Default status is ACTIVE."""
        station = StationFactory()
        assert station.status == DeviceStatus.ACTIVE
        assert station.is_active is True

    def test_station_timestamps_utc(self) -> None:
        """created_at and updated_at are UTC-aware datetimes."""
        import datetime

        station = StationFactory()
        assert station.created_at.tzinfo is not None
        assert station.created_at.tzinfo == datetime.timezone.utc or str(
            station.created_at.tzinfo
        ) in ("UTC", "utc")

    def test_station_owner_relationship(self) -> None:
        """Station links to its owner via reverse relation."""
        owner = StationOwnerFactory()
        s1 = StationFactory(owner=owner)
        s2 = StationFactory(owner=owner)
        assert owner.stations.count() == 2
        assert s1 in owner.stations.all()
        assert s2 in owner.stations.all()

    def test_station_code_unique(self) -> None:
        """Two stations with the same code cannot be created."""
        StationFactory(code="unique-code")
        with pytest.raises(IntegrityError):
            Station.objects.create(
                owner=StationOwnerFactory(),
                name="Duplicate",
                code="unique-code",
                latitude=Decimal("40.0"),
                longitude=Decimal("-3.0"),
                altitude_m=600,
            )

    def test_station_latitude_valid_range(self) -> None:
        """Latitude validator rejects values outside [-90, 90]."""
        station = StationFactory.build(latitude=Decimal("91.0"))
        with pytest.raises(ValidationError):
            station.full_clean()

    def test_station_longitude_valid_range(self) -> None:
        """Longitude validator rejects values outside [-180, 180]."""
        station = StationFactory.build(longitude=Decimal("181.0"))
        with pytest.raises(ValidationError):
            station.full_clean()

    def test_station_inactive_is_active_false(self) -> None:
        """is_active property returns False for non-ACTIVE statuses."""
        station = StationFactory(status=DeviceStatus.INACTIVE)
        assert station.is_active is False

        station.status = DeviceStatus.MAINTENANCE
        assert station.is_active is False

    def test_station_metadata_default_empty_dict(self) -> None:
        """metadata defaults to an empty dict, not None."""
        station = StationFactory()
        assert station.metadata == {}
        assert isinstance(station.metadata, dict)
