"""
API tests for user authentication endpoints.

@file   tests/test_users/test_auth_api.py
@author slopez.tech
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories import AdminUserFactory


@pytest.mark.django_db
@pytest.mark.api
class TestTokenObtainPair:
    """Tests for POST /api/v1/auth/token/"""

    def test_valid_credentials_return_tokens(self, api_client: APIClient) -> None:
        """Valid email+password must return access and refresh tokens."""
        password = "test-password-123!"
        user = AdminUserFactory(password=None)
        user.set_password(password)
        user.save()

        url = reverse("users:token-obtain")
        response = api_client.post(
            url,
            {"email": user.email, "password": password},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access" in data
        assert "refresh" in data

    def test_invalid_password_returns_401(self, api_client: APIClient) -> None:
        """Wrong password must return 401 Unauthorized."""
        user = AdminUserFactory()
        url = reverse("users:token-obtain")
        response = api_client.post(
            url,
            {"email": user.email, "password": "wrong-password"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_nonexistent_user_returns_401(self, api_client: APIClient) -> None:
        """Non-existent email must return 401 (not 404, to avoid user enumeration)."""
        url = reverse("users:token-obtain")
        response = api_client.post(
            url,
            {"email": "nonexistent@example.com", "password": "password"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_user_cannot_authenticate(self, api_client: APIClient) -> None:
        """Inactive users must not be able to obtain tokens."""
        password = "test-password-123!"
        user = AdminUserFactory(is_active=False)
        user.set_password(password)
        user.save()

        url = reverse("users:token-obtain")
        response = api_client.post(
            url,
            {"email": user.email, "password": password},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.api
class TestUserMeView:
    """Tests for GET /api/v1/auth/me/"""

    def test_authenticated_user_gets_profile(
        self, authenticated_admin_client: APIClient
    ) -> None:
        """Authenticated user must receive their profile data."""
        url = reverse("users:user-me")
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "email" in data
        assert "username" in data
        assert "role" in data
        assert "id" in data

    def test_unauthenticated_request_returns_401(self, api_client: APIClient) -> None:
        """Unauthenticated request to /me/ must return 401."""
        url = reverse("users:user-me")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_does_not_expose_password(
        self, authenticated_admin_client: APIClient
    ) -> None:
        """Profile endpoint must never expose the password field."""
        url = reverse("users:user-me")
        response = authenticated_admin_client.get(url)
        data = response.json()
        assert "password" not in data
