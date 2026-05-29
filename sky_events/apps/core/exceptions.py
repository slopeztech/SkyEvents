"""
Custom exception handler for DRF.

Produces consistent, RFC 7807 (Problem Details) compliant error responses
across all API endpoints.

RFC 7807 response format::

    {
        "type": "https://skyevents.example.com/errors/validation-error",
        "title": "Validation Error",
        "status": 422,
        "detail": "One or more fields failed validation.",
        "errors": {
            "field_name": ["error message"]
        }
    }

@file   sky_events/apps/core/exceptions.py
@author slopez.tech
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom application exceptions
# ---------------------------------------------------------------------------


class SkyEventsAPIException(APIException):
    """
    Base exception for all SkyEvents domain errors.

    Subclass this to add typed error codes for specific failure modes.
    """

    error_code: str = "skyevents_error"
    default_detail: str = "An unexpected error occurred."
    default_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        detail: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=detail or self.default_detail, code=code or self.error_code)


class ConflictError(SkyEventsAPIException):
    """Raised when a resource conflict prevents the operation (HTTP 409)."""

    error_code = "conflict"
    default_detail = "A resource conflict occurred."
    status_code = status.HTTP_409_CONFLICT


class ServiceUnavailableError(SkyEventsAPIException):
    """Raised when a downstream service is unavailable (HTTP 503)."""

    error_code = "service_unavailable"
    default_detail = "A required service is temporarily unavailable."
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class UnprocessableEntityError(SkyEventsAPIException):
    """Raised when the request is well-formed but semantically invalid (HTTP 422)."""

    error_code = "unprocessable_entity"
    default_detail = "The request could not be processed."
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# Exception handler
# ---------------------------------------------------------------------------

_STATUS_TITLES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Custom DRF exception handler.

    Converts all exceptions to RFC 7807 Problem Details format and logs
    server-side errors appropriately.

    @param  exc     The exception that was raised.
    @param  context The DRF context dict (view, request, args, kwargs).
    @return A ``Response`` object, or ``None`` if the exception is not handled.
    """
    # Translate Django exceptions to DRF equivalents
    if isinstance(exc, Http404):
        from rest_framework.exceptions import NotFound  # noqa: PLC0415

        exc = NotFound()
    elif isinstance(exc, PermissionDenied):
        from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied  # noqa: PLC0415

        exc = DRFPermissionDenied()
    elif isinstance(exc, ValidationError):
        from rest_framework.exceptions import ValidationError as DRFValidationError  # noqa: PLC0415

        exc = DRFValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

    # Let DRF handle the base formatting first
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception — let Django's default 500 handler take over
        logger.exception("Unhandled exception in API view", exc_info=exc)
        return None

    # Enrich with RFC 7807 fields
    status_code: int = response.status_code
    title: str = _STATUS_TITLES.get(status_code, "Error")

    # Build a structured error body
    error_data: dict[str, Any] = {
        "status": status_code,
        "title": title,
    }

    original_data = response.data

    if isinstance(original_data, dict):
        # Extract DRF's 'detail' field and any field errors
        if "detail" in original_data:
            error_data["detail"] = str(original_data["detail"])
        else:
            error_data["detail"] = title
            error_data["errors"] = original_data
    elif isinstance(original_data, list):
        error_data["detail"] = title
        error_data["errors"] = original_data
    else:
        error_data["detail"] = str(original_data)

    # Log 5xx errors as errors, 4xx as warnings
    if status_code >= 500:
        logger.error(
            "API server error",
            extra={
                "status_code": status_code,
                "path": context.get("request", {}).path if hasattr(context.get("request", {}), "path") else "",
            },
        )
    elif status_code >= 400:
        logger.warning(
            "API client error",
            extra={"status_code": status_code, "detail": error_data.get("detail", "")},
        )

    response.data = error_data
    return response
