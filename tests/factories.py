"""
Factory Boy factories for SkyEvents tests.

Factories are defined here and imported by test modules and conftest.
They use realistic fake data via the Faker library.

@file   tests/factories.py
@author slopez.tech
"""

from __future__ import annotations

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from sky_events.apps.camera.models import Camera, CameraType
from sky_events.apps.core.models import DeviceStatus
from sky_events.apps.radio.models import RadioReceiver
from sky_events.apps.station.models import Station
from sky_events.apps.users.models import User, UserRole


class UserFactory(DjangoModelFactory):
    """
    Base factory for User model.

    Generates realistic fake user data. Does NOT set a role —
    use AdminUserFactory or StationOwnerFactory instead.
    """

    class Meta:
        model = User
        django_get_or_create = ("email",)
        skip_postgeneration_save = True

    email = factory.Faker("email")
    username = factory.Faker("user_name")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    organisation = factory.Faker("company")
    country = factory.Faker("country_code", representation="alpha-2")
    timezone = "UTC"
    is_active = True
    is_staff = False
    password = factory.PostGenerationMethodCall("set_password", "test-password-123!")


class AdminUserFactory(UserFactory):
    """Factory for admin users."""

    role = UserRole.ADMIN
    is_staff = True
    email = factory.Sequence(lambda n: f"admin{n}@skyevents.test")
    username = factory.Sequence(lambda n: f"admin{n}")


class StationOwnerFactory(UserFactory):
    """Factory for station owner users."""

    role = UserRole.STATION_OWNER
    email = factory.Sequence(lambda n: f"owner{n}@skyevents.test")
    username = factory.Sequence(lambda n: f"owner{n}")


# ---------------------------------------------------------------------------
# Station factories
# ---------------------------------------------------------------------------


class StationFactory(DjangoModelFactory):
    """Factory for Station model."""

    class Meta:
        model = Station
        django_get_or_create = ("code",)

    owner = factory.SubFactory(StationOwnerFactory)
    name = factory.Sequence(lambda n: f"Station {n:04d}")
    code = factory.Sequence(lambda n: f"stn-{n:04d}")
    description = factory.Faker("sentence")
    # Madrid area as realistic default
    latitude = factory.LazyFunction(lambda: Decimal("40.416775"))
    longitude = factory.LazyFunction(lambda: Decimal("-3.703790"))
    altitude_m = 650
    timezone = "Europe/Madrid"
    status = DeviceStatus.ACTIVE


# ---------------------------------------------------------------------------
# Camera factories
# ---------------------------------------------------------------------------


class CameraFactory(DjangoModelFactory):
    """Factory for Camera model."""

    class Meta:
        model = Camera
        django_get_or_create = ("code",)

    station = factory.SubFactory(StationFactory)
    name = factory.Sequence(lambda n: f"Camera {n:04d}")
    code = factory.Sequence(lambda n: f"cam-{n:04d}")
    model_name = "IMX291"
    sensor_type = "CMOS"
    resolution_width = 1920
    resolution_height = 1080
    fps = 25
    camera_type = CameraType.FIXED
    field_of_view_deg = factory.LazyFunction(lambda: Decimal("90.00"))
    azimuth_deg = factory.LazyFunction(lambda: Decimal("0.00"))
    elevation_deg = factory.LazyFunction(lambda: Decimal("90.00"))
    status = DeviceStatus.ACTIVE


# ---------------------------------------------------------------------------
# RadioReceiver factories
# ---------------------------------------------------------------------------


class RadioReceiverFactory(DjangoModelFactory):
    """Factory for RadioReceiver model."""

    class Meta:
        model = RadioReceiver
        django_get_or_create = ("code",)

    station = factory.SubFactory(StationFactory)
    name = factory.Sequence(lambda n: f"Radio {n:04d}")
    code = factory.Sequence(lambda n: f"rdo-{n:04d}")
    receiver_model = "RTL-SDR v3"
    frequency_mhz = factory.LazyFunction(lambda: Decimal("143.050"))
    bandwidth_khz = factory.LazyFunction(lambda: Decimal("15.00"))
    antenna_type = "Yagi"
    polarization = "horizontal"
    software = "SDRSharp"
    status = DeviceStatus.ACTIVE

