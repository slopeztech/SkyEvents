"""
Custom pagination classes for SkyEvents API.

Follows RFC-compliant patterns with metadata in response body.

@file   sky_events/apps/core/pagination.py
@author slopez.tech
"""

from __future__ import annotations

from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for all SkyEvents API list endpoints.

    Response format::

        {
            "count": 123,
            "next": "https://api.example.com/resource/?page=2",
            "previous": null,
            "total_pages": 5,
            "current_page": 1,
            "page_size": 25,
            "results": [...]
        }
    """

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200
    page_query_param = "page"

    def get_paginated_response(self, data: list[Any]) -> Response:
        """Return paginated response with additional metadata."""
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Return OpenAPI schema for paginated responses."""
        return {
            "type": "object",
            "required": ["count", "results"],
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Total number of results across all pages.",
                },
                "next": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                    "description": "URL of the next page, or null if last page.",
                },
                "previous": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                    "description": "URL of the previous page, or null if first page.",
                },
                "total_pages": {
                    "type": "integer",
                    "description": "Total number of pages.",
                },
                "current_page": {
                    "type": "integer",
                    "description": "Current page number (1-indexed).",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of results per page.",
                },
                "results": schema,
            },
        }


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination for high-throughput endpoints (e.g., event ingestion history).

    Allows larger page sizes for bulk operations.
    """

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000
    page_query_param = "page"
