"""
Custom DRF permission classes for SkyEvents.

@file   sky_events/apps/core/api/permissions.py
@author slopez.tech
"""

from __future__ import annotations

import hmac

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView


class ScriptTokenPermission(IsAuthenticated):
    """
    Grants access only when the request carries BOTH a valid JWT and an
    ``X-Script-Token`` header whose value matches the authenticated user's
    ``script_token``.

    Authentication flow for station scripts
    ----------------------------------------
    1. Script POSTs credentials to ``/api/v1/auth/token/`` → receives JWT.
    2. All subsequent station-API calls include:
       - ``Authorization: Bearer <access_token>``
       - ``X-Script-Token: <user.script_token>``

    The second factor prevents a stolen JWT alone from accessing the
    station endpoints.
    """

    message = "Valid JWT and matching X-Script-Token header are required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not super().has_permission(request, view):
            return False

        provided = request.headers.get("X-Script-Token", "")
        stored = getattr(request.user, "script_token", "")

        # Both values must be non-empty; use timing-safe comparison to
        # prevent timing attacks on the token value.
        if not provided or not stored:
            return False

        return hmac.compare_digest(provided, stored)
