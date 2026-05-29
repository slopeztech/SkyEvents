"""
Root conftest.py for SkyEvents test suite.

Provides shared fixtures available across all test modules.

Fixture scopes used:
- ``session``  → created once per test session (expensive: DB connections)
- ``module``   → created once per test module
- ``function`` → created for each test function (default)

@file   tests/conftest.py
@author slopez.tech
"""

from __future__ import annotations

import pytest
from django.test import Client

from tests.factories import AdminUserFactory, StationOwnerFactory


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(db: None) -> "AdminUserFactory":
    """Create and return an admin user."""
    return AdminUserFactory()


@pytest.fixture
def station_owner(db: None) -> "StationOwnerFactory":
    """Create and return a station owner user."""
    return StationOwnerFactory()


# ---------------------------------------------------------------------------
# API client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client() -> Client:
    """Return an unauthenticated DRF APIClient."""
    from rest_framework.test import APIClient  # noqa: PLC0415

    return APIClient()


@pytest.fixture
def authenticated_admin_client(admin_user: "AdminUserFactory") -> Client:
    """Return a DRF APIClient authenticated as an admin user via JWT."""
    from rest_framework.test import APIClient  # noqa: PLC0415
    from rest_framework_simplejwt.tokens import RefreshToken  # noqa: PLC0415

    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def authenticated_owner_client(station_owner: "StationOwnerFactory") -> Client:
    """Return a DRF APIClient authenticated as a station owner via JWT."""
    from rest_framework.test import APIClient  # noqa: PLC0415
    from rest_framework_simplejwt.tokens import RefreshToken  # noqa: PLC0415

    client = APIClient()
    refresh = RefreshToken.for_user(station_owner)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client
