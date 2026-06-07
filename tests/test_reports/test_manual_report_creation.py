"""
Tests for manual report creation for non-admin users.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from sky_events.apps.events.models import AstronomicalEvent, EventStatus as EventStatusModel, EventType
from sky_events.apps.reports.models import ReportStatus, StationReport
from sky_events.apps.reports.views import _build_report_groups
from tests.factories import StationFactory, StationOwnerFactory


def _make_owner() -> object:
    """Create a persisted station-owner user for test login."""
    owner = StationOwnerFactory()
    owner.save()
    return owner


@pytest.mark.django_db
class TestManualReportCreation:
    def test_event_reports_are_grouped_in_event_cards(self) -> None:
        owner = _make_owner()
        station = StationFactory(owner=owner)
        event = AstronomicalEvent.objects.create(
            code="SE-2026-001",
            name="Meteor shower test",
            event_type=EventType.METEOR,
            status=EventStatusModel.PUBLISHED,
            detected_at=timezone.now(),
            created_by=owner,
        )
        report_one = StationReport.objects.create(
            station=station,
            event=event,
            recorded_at=timezone.now(),
            status=ReportStatus.PENDING,
            notes="First linked report",
        )
        report_two = StationReport.objects.create(
            station=station,
            event=event,
            recorded_at=timezone.now() + timezone.timedelta(minutes=1),
            status=ReportStatus.LINKED,
            notes="Second linked report",
        )

        groups = _build_report_groups([report_one, report_two])

        assert len(groups) == 1
        assert groups[0]["kind"] == "event"
        assert groups[0]["event"] == event
        assert groups[0]["count"] == 2
    def test_non_admin_can_open_manual_report_page(self) -> None:
        owner = _make_owner()
        station = StationFactory(owner=owner)

        client = Client()
        client.force_login(owner)

        response = client.get(reverse("reports:create"))

        assert response.status_code == 200
        assert "New report" in response.content.decode()
        assert str(station.pk) in response.content.decode()

    def test_non_admin_only_sees_own_stations_in_report_form(self) -> None:
        owner = _make_owner()
        owner_station = StationFactory(owner=owner)
        other_owner = _make_owner()
        StationFactory(owner=other_owner)

        client = Client()
        client.force_login(owner)

        response = client.get(reverse("reports:create"))

        assert response.status_code == 200
        station_choices = list(response.context["form"].fields["station"].queryset)
        assert owner_station in station_choices
        assert len(station_choices) == 1

    def test_non_admin_can_create_report_manually(self) -> None:
        owner = _make_owner()
        station = StationFactory(owner=owner)

        client = Client()
        client.force_login(owner)

        response = client.post(
            reverse("reports:create"),
            {
                "station": station.pk,
                "camera": "",
                "radio_receiver": "",
                "recorded_at": "2026-06-07T12:30",
                "duration_ms": "1500",
                "status": ReportStatus.PENDING,
                "notes": "Manual test report",
            },
            follow=False,
        )

        assert response.status_code == 302
        assert StationReport.objects.filter(
            station=station,
            notes="Manual test report",
            status=ReportStatus.PENDING,
        ).exists()
