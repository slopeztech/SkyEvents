"""
Unit and integration tests for the RadioReceiver model.

@file   tests/test_radios/test_models.py
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from sky_events.apps.core.models import DeviceStatus
from sky_events.apps.radio.models import RadioReceiver
from tests.factories import RadioReceiverFactory, StationFactory


@pytest.mark.django_db
class TestRadioReceiverModel:
    """Tests for RadioReceiver model creation and field behaviour."""

    def test_create_radio_receiver(self) -> None:
        """A RadioReceiver can be created with valid data."""
        radio = RadioReceiverFactory()
        assert radio.pk is not None

    def test_radio_str(self) -> None:
        """__str__ includes name, code, frequency and station code."""
        station = StationFactory(code="mad-north")
        radio = RadioReceiverFactory(
            station=station,
            name="GRAVES monitor",
            code="rdo-graves",
            frequency_mhz=Decimal("143.050"),
        )
        assert str(radio) == "GRAVES monitor [rdo-graves] 143.050 MHz @ mad-north"

    def test_radio_station_relationship(self) -> None:
        """Station.radio_receivers reverse relation returns all receivers."""
        station = StationFactory()
        r1 = RadioReceiverFactory(station=station)
        r2 = RadioReceiverFactory(station=station)
        assert station.radio_receivers.count() == 2
        assert r1 in station.radio_receivers.all()
        assert r2 in station.radio_receivers.all()

    def test_radio_code_unique(self) -> None:
        """Two radio receivers with the same code cannot be created."""
        station = StationFactory()
        RadioReceiverFactory(station=station, code="rdo-unique")
        with pytest.raises(IntegrityError):
            RadioReceiver.objects.create(
                station=station,
                name="Duplicate",
                code="rdo-unique",
                frequency_mhz=Decimal("49.990"),
            )

    def test_radio_default_status_active(self) -> None:
        """Default status is ACTIVE."""
        radio = RadioReceiverFactory()
        assert radio.status == DeviceStatus.ACTIVE
        assert radio.is_active is True

    def test_radio_frequency_non_negative(self) -> None:
        """frequency_mhz validator rejects negative values."""
        radio = RadioReceiverFactory.build(frequency_mhz=Decimal("-1.0"))
        with pytest.raises(ValidationError):
            radio.full_clean()

    def test_radio_bandwidth_non_negative(self) -> None:
        """bandwidth_khz validator rejects negative values."""
        radio = RadioReceiverFactory.build(bandwidth_khz=Decimal("-1.0"))
        with pytest.raises(ValidationError):
            radio.full_clean()

    def test_radio_technical_params_default_empty_dict(self) -> None:
        """technical_params defaults to an empty dict."""
        radio = RadioReceiverFactory()
        assert radio.technical_params == {}

    def test_radio_cascade_delete_on_station_delete(self) -> None:
        """Deleting a station cascades to its radio receivers."""
        station = StationFactory()
        radio_id = RadioReceiverFactory(station=station).pk
        station.delete()
        assert not RadioReceiver.objects.filter(pk=radio_id).exists()

    def test_radio_inactive_is_active_false(self) -> None:
        """is_active returns False for non-ACTIVE statuses."""
        radio = RadioReceiverFactory(status=DeviceStatus.MAINTENANCE)
        assert radio.is_active is False

    def test_station_can_have_multiple_radios_and_cameras(self) -> None:
        """A station can simultaneously have cameras and radio receivers."""
        from tests.factories import CameraFactory

        station = StationFactory()
        CameraFactory(station=station)
        CameraFactory(station=station)
        RadioReceiverFactory(station=station)
        assert station.cameras.count() == 2
        assert station.radio_receivers.count() == 1
