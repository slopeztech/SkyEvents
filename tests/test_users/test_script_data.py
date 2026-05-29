"""
Tests for ScriptDataView — admin download of script configuration files.

Covers:
- Access control (admin only)
- HTML page (GET 200 with correct context)
- JSON download (GET ?format=json → attachment)
- JSON structure and content
- Uniqueness of script_token, hash_id fields
- Edge cases: user with no stations

@file   tests/test_users/test_script_data.py
@author slopez.tech
"""

from __future__ import annotations

import json

import pytest
from django.test import Client
from django.urls import reverse

from tests.factories import (
    AdminUserFactory,
    CameraFactory,
    RadioReceiverFactory,
    StationFactory,
    StationOwnerFactory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _script_data_url(pk: object) -> str:
    return reverse("accounts:script-data", kwargs={"pk": pk})


def _make_admin():
    """
    Create an admin user with the hashed password properly persisted to DB.

    The UserFactory uses ``skip_postgeneration_save=True``, which means
    ``set_password`` is called in memory but never flushed to the DB.
    A manual ``save()`` is required so Django's session-auth-hash check
    (used by ``force_login``) passes.
    """
    user = AdminUserFactory()
    user.save()
    return user


def _make_owner():
    """Create a station owner with properly persisted password (same reason)."""
    user = StationOwnerFactory()
    user.save()
    return user


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestScriptDataViewAccess:
    """Only admin users may access the script-data page."""

    def test_anonymous_redirected_to_login(self) -> None:
        """Unauthenticated requests must be redirected."""
        owner = StationOwnerFactory()
        client = Client()
        response = client.get(_script_data_url(owner.pk))
        assert response.status_code == 302

    def test_station_owner_denied(self) -> None:
        """Station owners (non-admin) must receive a 403 or redirect."""
        owner = _make_owner()
        another_owner = _make_owner()
        client = Client()
        client.force_login(owner)
        response = client.get(_script_data_url(another_owner.pk))
        # Our AdminRequiredMixin returns 403 or redirects to login
        assert response.status_code in (302, 403)

    def test_admin_can_access_any_user(self) -> None:
        """Admin users must get HTTP 200 for any user's script-data page."""
        admin = _make_admin()
        owner = _make_owner()
        client = Client()
        client.force_login(admin)
        response = client.get(_script_data_url(owner.pk))
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# HTML page context
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestScriptDataViewHTML:
    """HTML page renders with correct context variables."""

    def test_context_contains_script_data_json(self) -> None:
        """Context must include 'script_data_json' (a JSON string)."""
        admin = _make_admin()
        owner = _make_owner()
        client = Client()
        client.force_login(admin)
        response = client.get(_script_data_url(owner.pk))
        assert "script_data_json" in response.context
        # Must be valid JSON
        parsed = json.loads(response.context["script_data_json"])
        assert isinstance(parsed, dict)

    def test_context_totals_for_user_without_stations(self) -> None:
        """User with no stations: cameras_total and radios_total must be 0."""
        admin = _make_admin()
        owner = _make_owner()
        client = Client()
        client.force_login(admin)
        response = client.get(_script_data_url(owner.pk))
        assert response.context["cameras_total"] == 0
        assert response.context["radios_total"] == 0

    def test_context_totals_for_user_with_devices(self) -> None:
        """cameras_total and radios_total reflect all devices across all stations."""
        admin = _make_admin()
        owner = _make_owner()
        station1 = StationFactory(owner=owner)
        station2 = StationFactory(owner=owner)
        CameraFactory(station=station1)
        CameraFactory(station=station1)
        CameraFactory(station=station2)
        RadioReceiverFactory(station=station1)
        RadioReceiverFactory(station=station2)
        client = Client()
        client.force_login(admin)
        response = client.get(_script_data_url(owner.pk))
        assert response.context["cameras_total"] == 3
        assert response.context["radios_total"] == 2

    def test_context_account_is_target_user(self) -> None:
        """The 'account' context variable must be the target user, not the admin."""
        admin = _make_admin()
        owner = _make_owner()
        client = Client()
        client.force_login(admin)
        response = client.get(_script_data_url(owner.pk))
        assert response.context["account"].pk == owner.pk


# ---------------------------------------------------------------------------
# JSON download
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestScriptDataViewJSONDownload:
    """GET ?format=json returns a downloadable JSON file."""

    def _get_json(self, admin: object, target: object) -> tuple:
        """Helper: fetch JSON download and return (response, parsed_data)."""
        client = Client()
        client.force_login(admin)
        response = client.get(_script_data_url(target.pk) + "?format=json")
        return response, json.loads(response.content)

    def test_returns_200_json_content_type(self) -> None:
        admin = _make_admin()
        owner = _make_owner()
        response, _ = self._get_json(admin, owner)
        assert response.status_code == 200
        assert "application/json" in response["Content-Type"]

    def test_content_disposition_attachment(self) -> None:
        """Response must have Content-Disposition: attachment."""
        admin = _make_admin()
        owner = _make_owner()
        response, _ = self._get_json(admin, owner)
        assert "attachment" in response["Content-Disposition"]

    def test_filename_contains_username(self) -> None:
        """Attachment filename must contain the target user's username."""
        admin = _make_admin()
        owner = _make_owner()
        response, _ = self._get_json(admin, owner)
        assert owner.username in response["Content-Disposition"]

    def test_top_level_keys_present(self) -> None:
        """JSON must have skyevents_version, generated_at, user_token, stations."""
        admin = _make_admin()
        owner = _make_owner()
        _, data = self._get_json(admin, owner)
        assert data["skyevents_version"] == "1.0"
        assert "generated_at" in data
        assert "user_token" in data
        assert "stations" in data

    def test_user_token_matches_model(self) -> None:
        """user_token in JSON must equal owner.script_token."""
        admin = _make_admin()
        owner = _make_owner()
        _, data = self._get_json(admin, owner)
        assert data["user_token"] == owner.script_token

    def test_empty_stations_for_user_without_stations(self) -> None:
        """User with no stations must return stations: []."""
        admin = _make_admin()
        owner = _make_owner()
        _, data = self._get_json(admin, owner)
        assert data["stations"] == []

    def test_station_structure_in_json(self) -> None:
        """Each station entry must include hash_id, name, code, cameras, radios."""
        admin = _make_admin()
        owner = _make_owner()
        station = StationFactory(owner=owner)
        _, data = self._get_json(admin, owner)
        assert len(data["stations"]) == 1
        s = data["stations"][0]
        assert s["hash_id"] == station.hash_id
        assert s["name"] == station.name
        assert s["code"] == station.code
        assert "cameras" in s
        assert "radios" in s

    def test_camera_hash_id_in_json(self) -> None:
        """Camera entries in JSON must include their hash_id."""
        admin = _make_admin()
        owner = _make_owner()
        station = StationFactory(owner=owner)
        cam = CameraFactory(station=station)
        _, data = self._get_json(admin, owner)
        cam_entry = data["stations"][0]["cameras"][0]
        assert cam_entry["hash_id"] == cam.hash_id
        assert cam_entry["name"] == cam.name
        assert cam_entry["code"] == cam.code

    def test_radio_hash_id_in_json(self) -> None:
        """Radio entries in JSON must include their hash_id."""
        admin = _make_admin()
        owner = _make_owner()
        station = StationFactory(owner=owner)
        radio = RadioReceiverFactory(station=station)
        _, data = self._get_json(admin, owner)
        radio_entry = data["stations"][0]["radios"][0]
        assert radio_entry["hash_id"] == radio.hash_id
        assert radio_entry["name"] == radio.name
        assert radio_entry["code"] == radio.code

    def test_multiple_stations_in_json(self) -> None:
        """User with multiple stations must have all of them in JSON."""
        admin = _make_admin()
        owner = _make_owner()
        StationFactory(owner=owner)
        StationFactory(owner=owner)
        _, data = self._get_json(admin, owner)
        assert len(data["stations"]) == 2

    def test_anonymous_cannot_download_json(self) -> None:
        """Unauthenticated requests to ?format=json must be redirected."""
        owner = StationOwnerFactory()
        client = Client()
        response = client.get(_script_data_url(owner.pk) + "?format=json")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Model field uniqueness and auto-generation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestScriptTokenUniqueness:
    """script_token on User is auto-generated and unique."""

    def test_script_token_is_set_on_creation(self) -> None:
        """A new user must have a non-empty script_token."""
        user = StationOwnerFactory()
        assert user.script_token
        assert len(user.script_token) > 0

    def test_script_tokens_are_unique_across_users(self) -> None:
        """Two different users must have different script_tokens."""
        user1 = StationOwnerFactory()
        user2 = StationOwnerFactory()
        assert user1.script_token != user2.script_token

    def test_script_token_min_length(self) -> None:
        """script_token generated by secrets.token_urlsafe(32) must be ≥ 40 chars."""
        user = StationOwnerFactory()
        # token_urlsafe(32) produces ~43 chars of base64url
        assert len(user.script_token) >= 40


@pytest.mark.django_db
class TestHashIDUniqueness:
    """hash_id on Station, Camera, RadioReceiver is auto-generated and unique."""

    def test_station_hash_id_set_on_creation(self) -> None:
        station = StationFactory()
        assert station.hash_id
        assert len(station.hash_id) == 24  # token_hex(12) → 24 hex chars

    def test_camera_hash_id_set_on_creation(self) -> None:
        cam = CameraFactory()
        assert cam.hash_id
        assert len(cam.hash_id) == 24

    def test_radio_hash_id_set_on_creation(self) -> None:
        radio = RadioReceiverFactory()
        assert radio.hash_id
        assert len(radio.hash_id) == 24

    def test_station_hash_ids_are_unique(self) -> None:
        s1 = StationFactory()
        s2 = StationFactory()
        assert s1.hash_id != s2.hash_id

    def test_camera_hash_ids_are_unique(self) -> None:
        c1 = CameraFactory()
        c2 = CameraFactory()
        assert c1.hash_id != c2.hash_id

    def test_radio_hash_ids_are_unique(self) -> None:
        r1 = RadioReceiverFactory()
        r2 = RadioReceiverFactory()
        assert r1.hash_id != r2.hash_id
