"""
@file   Reporter/api/client.py
@brief  HTTP client for the SkyEvents station REST API.

Wraps the three station endpoints and handles serialisation, error
reporting, and multipart file upload.  Authentication headers are
injected automatically via the :class:`~auth.client.AuthClient`.
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from auth.client import AuthClient

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """
    Raised when the SkyEvents API returns an error response.

    @var status_code  HTTP status code.
    @var detail       Error message extracted from the response body.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        super().__init__(f"API error {status_code}: {detail}")


class SkyEventsApiClient:
    """
    HTTP client for the SkyEvents station API (``/api/v1/station/``).

    All methods inject the required ``Authorization`` and
    ``X-Script-Token`` headers via the injected :class:`AuthClient`.

    A single :class:`requests.Session` is reused across all calls for
    efficient connection pooling.

    @var _base_url  API base URL (e.g. ``https://…/api/v1``).
    @var _auth      Authentication client used to obtain request headers.
    @var _timeout   Per-request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        auth: AuthClient,
        timeout: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = auth
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def create_report(self, payload: dict) -> dict:
        """
        Create a detection report.

        Corresponds to ``POST /api/v1/station/reports/``.

        @param payload  Dict matching the ``StationReportCreateSerializer``
                        schema (station_hash_id, recorded_at, files, …).
        @return         Response body with ``id`` and ``status``.
        @raises ApiError on HTTP errors.
        """
        return self._request("POST", "/station/reports/", json=payload)

    def list_requirements(self) -> list[dict]:
        """
        Retrieve all pending media requirements for the authenticated user.

        Corresponds to ``GET /api/v1/station/requirements/``.

        @return  List of requirement objects (id, station_code,
                 requested_paths, status, …).
        @raises  ApiError on HTTP errors.
        """
        result = self._request("GET", "/station/requirements/")
        # Handle both plain list and paginated responses.
        if isinstance(result, list):
            return result
        return result.get("results", [])

    def upload_attachment(
        self,
        requirement_id: str,
        file_path: Path,
        original_path: str,
        file_type: str,
    ) -> dict:
        """
        Upload a file to fulfil a media requirement.

        Corresponds to ``POST /api/v1/station/requirements/{id}/media/``.

        @param requirement_id  UUID of the :class:`MediaRequirement`.
        @param file_path       Local path to the file to upload.
        @param original_path   The path as it appears in ``requested_paths``
                               (i.e. the station-local path the admin requested).
        @param file_type       SkyEvents file type string
                               (``video``, ``image``, ``spectrogram``, …).
        @return                Response body with ``id`` and ``requirement_status``.
        @raises ApiError       On HTTP errors.
        @raises FileNotFoundError  If ``file_path`` does not exist.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Upload source file not found: {file_path}")

        with file_path.open("rb") as fh:
            return self._request(
                "POST",
                f"/station/requirements/{requirement_id}/media/",
                data={
                    "original_path": original_path,
                    "file_type": file_type,
                },
                files={"file": (file_path.name, fh)},
            )

    def ping(self, station_hash_id: str) -> dict:
        """
        Send a heartbeat ping for the given station.

        Corresponds to ``POST /api/v1/station/ping/``.

        @param station_hash_id  The station's ``hash_id``.
        @return                 Response body (``{"status": "ok"}``).
        @raises ApiError        On HTTP errors.
        """
        return self._request(
            "POST",
            "/station/ping/",
            json={"station_hash_id": station_hash_id},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        """
        Execute an authenticated HTTP request and return the parsed JSON body.

        @param method  HTTP method (``GET``, ``POST``, …).
        @param path    Relative path appended to the base URL.
        @param kwargs  Additional keyword arguments forwarded to
                       :meth:`requests.Session.request`.
        @return        Parsed JSON (dict or list).
        @raises ApiError  On any non-2xx HTTP status code.
        """
        headers = self._auth.get_headers()
        # When uploading files the Content-Type must be auto-set by requests
        # (multipart boundary is generated automatically); do not override it.
        if "files" not in kwargs:
            headers["Content-Type"] = "application/json"
        headers.update(kwargs.pop("headers", {}))

        url = self._url(path)
        logger.debug("%s %s", method, url)

        try:
            resp = self._session.request(
                method,
                url,
                headers=headers,
                timeout=self._timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise ApiError(0, f"Network error: {exc}") from exc

        if not resp.ok:
            try:
                body = resp.json()
                detail = body.get("detail") or body.get("errors") or resp.text[:300]
            except Exception:
                detail = resp.text[:300]
            raise ApiError(resp.status_code, str(detail))

        if resp.content:
            return resp.json()
        return {}

    def close(self) -> None:
        """Close the underlying :class:`requests.Session`."""
        self._session.close()

    def __enter__(self) -> SkyEventsApiClient:
        return self

    def __exit__(self, *_) -> None:
        self.close()
