"""
Tests for the users application.

@file   tests/test_users/test_models.py
@author slopez.tech
"""

from __future__ import annotations

import pytest

from sky_events.apps.users.models import User, UserRole
from tests.factories import AdminUserFactory, StationOwnerFactory, UserFactory


@pytest.mark.django_db
class TestUserManager:
    """Tests for the custom UserManager."""

    def test_create_user_requires_email(self) -> None:
        """create_user must raise ValueError when email is empty."""
        with pytest.raises(ValueError, match="email"):
            User.objects.create_user(email="", username="testuser", password="pass")

    def test_create_user_requires_username(self) -> None:
        """create_user must raise ValueError when username is empty."""
        with pytest.raises(ValueError, match="username"):
            User.objects.create_user(email="test@example.com", username="", password="pass")

    def test_create_user_normalises_email(self) -> None:
        """Email domain must be lowercased on creation."""
        user = User.objects.create_user(
            email="Test@EXAMPLE.COM",
            username="testuser",
            password="test-password-123!",
        )
        assert user.email == "Test@example.com"

    def test_create_superuser_sets_flags(self) -> None:
        """create_superuser must set is_staff, is_superuser, role=ADMIN."""
        user = User.objects.create_superuser(
            email="super@example.com",
            username="superuser",
            password="test-password-123!",
        )
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.role == UserRole.ADMIN

    def test_create_superuser_rejects_non_staff(self) -> None:
        """create_superuser must raise ValueError if is_staff=False."""
        with pytest.raises(ValueError, match="is_staff"):
            User.objects.create_superuser(
                email="super@example.com",
                username="superuser",
                password="pass",
                is_staff=False,
            )


@pytest.mark.django_db
class TestUserModel:
    """Tests for the User model."""

    def test_str_returns_email(self) -> None:
        """User __str__ must return the email address."""
        user = UserFactory(email="test@example.com")
        assert str(user) == "test@example.com"

    def test_get_full_name(self) -> None:
        """get_full_name must return 'First Last'."""
        user = UserFactory(first_name="Jane", last_name="Doe")
        assert user.get_full_name() == "Jane Doe"

    def test_get_full_name_falls_back_to_email(self) -> None:
        """get_full_name must return email when name fields are empty."""
        user = UserFactory(first_name="", last_name="", email="fallback@example.com")
        assert user.get_full_name() == "fallback@example.com"

    def test_is_admin_property(self) -> None:
        """is_admin must return True for ADMIN role only."""
        admin = AdminUserFactory()
        owner = StationOwnerFactory()
        assert admin.is_admin is True
        assert owner.is_admin is False

    def test_is_station_owner_property(self) -> None:
        """is_station_owner must return True for STATION_OWNER role only."""
        owner = StationOwnerFactory()
        admin = AdminUserFactory()
        assert owner.is_station_owner is True
        assert admin.is_station_owner is False

    def test_user_has_uuid_primary_key(self) -> None:
        """User primary key must be a UUID."""
        import uuid  # noqa: PLC0415

        user = UserFactory()
        assert isinstance(user.id, uuid.UUID)

    def test_default_role_is_station_owner(self) -> None:
        """Newly created users must default to STATION_OWNER role."""
        user = UserFactory()
        assert user.role == UserRole.STATION_OWNER
