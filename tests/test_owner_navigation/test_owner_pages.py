"""Regression tests for owner navigation pages."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from sky_events.apps.reports.models import StationReport
from tests.factories import CameraFactory, RadioReceiverFactory, StationFactory, StationOwnerFactory


@pytest.mark.django_db
class TestOwnerNavigationPages:
    def test_station_owner_can_open_station_list(self) -> None:
        owner = StationOwnerFactory()
        owner.save()
        StationFactory(owner=owner)

        client = Client()
        client.force_login(owner)

        response = client.get(reverse("station:list"))

        assert response.status_code == 200
        assert b"Stations" in response.content

    def test_station_owner_can_open_camera_and_radio_lists(self) -> None:
        owner = StationOwnerFactory()
        owner.save()
        station = StationFactory(owner=owner)
        CameraFactory(station=station)
        RadioReceiverFactory(station=station)

        client = Client()
        client.force_login(owner)

        camera_response = client.get(reverse("camera:list"))
        radio_response = client.get(reverse("radio:list"))

        assert camera_response.status_code == 200
        assert radio_response.status_code == 200
        assert b"Cameras" in camera_response.content
        assert b"Radio Receivers" in radio_response.content

    def test_owner_dashboard_shows_owned_stations_in_table(self) -> None:
        owner = StationOwnerFactory()
        owner.save()
        station = StationFactory(owner=owner)

        client = Client()
        client.force_login(owner)

        response = client.get(reverse("web:dashboard"))

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert station.name in content
        assert "Station list coming soon" not in content

    def test_owner_dashboard_shows_recent_reports_card(self) -> None:
        owner = StationOwnerFactory()
        owner.save()
        station = StationFactory(owner=owner)
        StationReport.objects.create(
            station=station,
            recorded_at="2026-06-07T12:00:00Z",
            status="pending",
            notes="Recent report",
        )

        client = Client()
        client.force_login(owner)

        response = client.get(reverse("web:dashboard"))

        assert response.status_code == 200
        assert "Mis últimos reportes" in response.content.decode("utf-8")
