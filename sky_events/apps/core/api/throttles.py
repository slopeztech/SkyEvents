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
