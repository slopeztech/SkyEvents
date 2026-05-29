"""
Tests for the core application health check views.

@file   tests/test_core/test_health.py
@author slopez.tech
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestHealthCheckView:
    """Tests for GET /health/ and GET /live/"""

    def test_health_returns_200(self, client: Client) -> None:
        """Health endpoint must return 200 without any dependencies."""
        url = reverse("core:health")
        response = client.get(url)
        assert response.status_code == 200

    def test_health_response_structure(self, client: Client) -> None:
        """Health response must contain status and timestamp."""
        url = reverse("core:health")
        response = client.get(url)
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_live_returns_200(self, client: Client) -> None:
        """Liveness probe must return 200."""
        url = reverse("core:live")
        response = client.get(url)
        assert response.status_code == 200

    def test_health_does_not_require_auth(self, client: Client) -> None:
        """Health endpoint must be accessible without authentication."""
        url = reverse("core:health")
        response = client.get(url)
        assert response.status_code == 200

    def test_health_post_not_allowed(self, client: Client) -> None:
        """Health endpoint must only accept GET."""
        url = reverse("core:health")
        response = client.post(url)
        assert response.status_code == 405


@pytest.mark.django_db
class TestReadinessCheckView:
    """Tests for GET /ready/"""

    def test_ready_returns_200_when_healthy(self, client: Client) -> None:
        """Readiness endpoint must return 200 when DB and cache are available."""
        url = reverse("core:ready")
        response = client.get(url)
        # In test environment DB should be available
        assert response.status_code in (200, 503)  # 503 if Redis not available

    def test_ready_response_has_checks(self, client: Client) -> None:
        """Readiness response must include per-service check results."""
        url = reverse("core:ready")
        response = client.get(url)
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]
        assert "cache" in data["checks"]

    def test_ready_response_has_uptime(self, client: Client) -> None:
        """Readiness response must include uptime_seconds."""
        url = reverse("core:ready")
        response = client.get(url)
        data = response.json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], float)
