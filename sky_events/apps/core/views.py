"""
Health check views for SkyEvents.

Implements three standard endpoints used by load balancers and orchestrators:

- ``/health/``  → Basic liveness probe. Returns 200 if the app is running.
- ``/ready/``   → Readiness probe. Checks DB + Redis connectivity.
- ``/live/``    → Kubernetes liveness probe (alias of /health/).

These endpoints are intentionally NOT authenticated — they are used by
infrastructure tooling (Kubernetes, HAProxy, AWS ELB) that cannot authenticate.

Security note: these endpoints return minimal information to avoid leaking
internal topology. They never expose connection strings or detailed errors.

@file   sky_events/apps/core/views.py
@author slopez.tech
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.core.cache import cache
from django.db import connection, OperationalError
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views import View

logger = logging.getLogger(__name__)

# Application start time for uptime reporting
_APP_START_TIME: float = time.monotonic()


class HealthCheckView(View):
    """
    Basic liveness probe.

    Returns HTTP 200 immediately without checking dependencies.
    Used to verify the application process is running.

    GET /health/
    GET /live/
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Return basic liveness status."""
        return JsonResponse(
            {
                "status": "ok",
                "timestamp": timezone.now().isoformat(),
            },
            status=200,
        )


class ReadinessCheckView(View):
    """
    Readiness probe that checks all critical dependencies.

    Returns HTTP 200 only when the application is fully ready to serve traffic.
    Returns HTTP 503 if any critical dependency is unavailable.

    Used by load balancers to route traffic only to healthy instances.

    GET /ready/
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Check all dependencies and return readiness status."""
        checks: dict[str, dict[str, Any]] = {}
        all_healthy = True

        # --- Database check ---
        db_healthy, db_info = self._check_database()
        checks["database"] = db_info
        if not db_healthy:
            all_healthy = False

        # --- Cache / Redis check ---
        cache_healthy, cache_info = self._check_cache()
        checks["cache"] = cache_info
        if not cache_healthy:
            all_healthy = False

        status_code = 200 if all_healthy else 503
        overall_status = "ok" if all_healthy else "degraded"

        if not all_healthy:
            logger.warning("Readiness check failed", extra={"checks": checks})

        return JsonResponse(
            {
                "status": overall_status,
                "timestamp": timezone.now().isoformat(),
                "uptime_seconds": round(time.monotonic() - _APP_START_TIME, 2),
                "checks": checks,
            },
            status=status_code,
        )

    @staticmethod
    def _check_database() -> tuple[bool, dict[str, Any]]:
        """
        Verify PostgreSQL connectivity by executing a trivial query.

        @return Tuple of (is_healthy, info_dict).
        """
        try:
            start = time.monotonic()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            return True, {"status": "ok", "latency_ms": latency_ms}
        except OperationalError as exc:
            logger.error("Database health check failed", exc_info=exc)
            return False, {"status": "error", "detail": "Database unreachable"}

    @staticmethod
    def _check_cache() -> tuple[bool, dict[str, Any]]:
        """
        Verify Redis connectivity via a ping/set/get round-trip.

        @return Tuple of (is_healthy, info_dict).
        """
        _probe_key = "skyevents:healthcheck:probe"
        _probe_value = "1"

        try:
            start = time.monotonic()
            cache.set(_probe_key, _probe_value, timeout=10)
            result = cache.get(_probe_key)
            latency_ms = round((time.monotonic() - start) * 1000, 2)

            if result != _probe_value:
                return False, {"status": "error", "detail": "Cache read/write mismatch"}

            return True, {"status": "ok", "latency_ms": latency_ms}
        except Exception as exc:  # noqa: BLE001
            logger.error("Cache health check failed", exc_info=exc)
            return False, {"status": "error", "detail": "Cache unreachable"}
