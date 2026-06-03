"""
Custom DRF throttle classes for SkyEvents.

@file   sky_events/apps/core/api/throttles.py
@author slopez.tech
"""

from __future__ import annotations

from rest_framework.throttling import UserRateThrottle


class StationThrottle(UserRateThrottle):
    """
    Rate limiter for station-script API calls.

    Scope ``station`` is configured in ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]``
    (base.py: ``"station": "10000/hour"``).
    """

    scope = "station"


class PingThrottle(UserRateThrottle):
    """
    Strict rate limiter for the heartbeat ping endpoint.

    Allows at most 1 request per 5 seconds per authenticated user so that
    a misconfigured reporter cannot flood the database with UPDATE queries.
    Scope ``ping`` must be declared in ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]``.
    """

    scope = "ping"
