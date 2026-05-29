"""
Security utilities for SkyEvents.

Provides:
- Custom axes lockout response (returns JSON instead of HTML)
- Security-related helper functions

@file   sky_events/apps/core/security.py
@author slopez.tech
"""

from __future__ import annotations

import logging

from django.http import HttpRequest, JsonResponse

logger = logging.getLogger(__name__)


def axes_lockout_response(request: HttpRequest, credentials: dict | None = None) -> JsonResponse:
    """
    Return a JSON 429 response when django-axes locks out an account.

    This replaces the default HTML lockout page with a proper API response.

    @param  request     The Django HTTP request.
    @param  credentials The credentials used in the failed attempt (not logged).
    @return A 429 JSON response.
    """
    logger.warning(
        "Account lockout triggered",
        extra={
            "ip": request.META.get("REMOTE_ADDR", "unknown"),
            "path": request.path,
        },
    )
    return JsonResponse(
        {
            "status": 429,
            "title": "Too Many Requests",
            "detail": (
                "Too many failed login attempts. "
                "Your account has been temporarily locked. "
                "Please try again later or contact support."
            ),
        },
        status=429,
    )
