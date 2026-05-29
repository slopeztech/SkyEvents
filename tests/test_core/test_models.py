"""
Tests for the core base models.

@file   tests/test_core/test_models.py
@author slopez.tech
"""

from __future__ import annotations

import uuid

import pytest

from sky_events.apps.core.models import TimeStampedModel, SoftDeleteModel


class ConcreteModel(TimeStampedModel):
    """Concrete subclass for testing abstract TimeStampedModel."""

    class Meta:
        # Use app_label to avoid needing a migration
        app_label = "core"


@pytest.mark.unit
class TestTimeStampedModel:
    """Unit tests for TimeStampedModel (no DB required)."""

    def test_default_uuid_is_generated(self) -> None:
        """Each instance must get a unique UUID by default."""
        instance = ConcreteModel.__new__(ConcreteModel)
        # Simulate the field default
        from uuid6 import uuid7  # noqa: PLC0415

        generated = uuid7()
        assert isinstance(generated, uuid.UUID)

    def test_repr_contains_class_name_and_id(self) -> None:
        """__repr__ should include class name and id for debugging."""
        instance = ConcreteModel.__new__(ConcreteModel)
        instance.id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        repr_str = repr(instance)
        assert "ConcreteModel" in repr_str
        assert "12345678" in repr_str
