"""
@file   Reporter/auth/client.py
@brief  JWT authentication client for the SkyEvents API.

Handles token acquisition, transparent refresh, and provides the
two-factor authentication headers required by all station endpoints:

  - ``Authorization: Bearer <access_token>``
  - ``X-Script-Token: <script_token>``

Thread-safe: a :class:`threading.Lock` protects token state so the
client can safely be shared across threads.
"""

from __future__ import annotations

import base64
import json
import logging
import threading
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when authentication or token refresh fails."""


class AuthClient:
    """
    Manages JWT authentication for the SkyEvents station API.

    Usage::

        auth = AuthClient(
            base_url="https://skyevents.example.com/api/v1",
            email="owner1@example.com",
            password="secret",
            script_token="",        # fetched automatically if empty
            refresh_margin=300,
        )
        auth.authenticate()          # obtain initial JWT pair
        headers = auth.get_headers() # use on every API request

    @var base_url       API base URL (``/api/v1`` prefix included).
    @var email          Station owner e-mail address.
    @var password       Station owner password.
    @var script_token   Script token for the second auth factor.  If empty,
                        it is fetched automatically from ``/auth/me/``.
    @var refresh_margin Refresh the access token this many seconds early.
    """

    def __init__(
        self,
        base_url: str,
        email: str,
        password: str,
        script_token: str = "",
        refresh_margin: int = 300,
        timeout: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._email = email
        self._password = password
        self._script_token = script_token
        self._refresh_margin = refresh_margin
        self._timeout = timeout

        self._access_token: str = ""
        self._refresh_token: str = ""
        self._access_expires_at: datetime = datetime.min.replace(tzinfo=timezone.utc)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def authenticate(self) -> None:
        """
        Obtain an initial JWT pair using email and password.

        If ``script_token`` was not provided in the configuration it is
        fetched automatically from ``/auth/me/`` after login.

        @raises AuthError  On HTTP errors or missing ``script_token``.
        """
        url = f"{self._base_url}/auth/token/"
        try:
            resp = requests.post(
                url,
                json={"email": self._email, "password": self._password},
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise AuthError(
                f"Authentication failed (HTTP {exc.response.status_code}): "
                f"{exc.response.text[:200]}"
            ) from exc
        except requests.RequestException as exc:
            raise AuthError(f"Authentication request failed: {exc}") from exc

        data = resp.json()
        self._store_tokens(data["access"], data["refresh"])

        if not self._script_token:
            self._fetch_script_token()

        logger.info("Authenticated as '%s'", self._email)

    def get_headers(self) -> dict[str, str]:
        """
        Return the HTTP headers required for authenticated station-API calls.

        Transparently refreshes the access token if it is close to expiry.

        @return  Dict with ``Authorization`` and ``X-Script-Token`` headers.
        @raises  AuthError if re-authentication fails.
        """
        with self._lock:
            self._ensure_valid_token()
            return {
                "Authorization": f"Bearer {self._access_token}",
                "X-Script-Token": self._script_token,
            }

    @property
    def script_token(self) -> str:
        """The script token value (read-only)."""
        return self._script_token

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _store_tokens(self, access: str, refresh: str) -> None:
        """
        Persist tokens in memory and parse the access token expiry.

        The JWT payload is base64-decoded without signature verification;
        the server is responsible for actual validation.

        @param access   JWT access token string.
        @param refresh  JWT refresh token string.
        """
        exp = self._parse_jwt_expiry(access)
        self._access_token = access
        self._refresh_token = refresh
        self._access_expires_at = exp

    @staticmethod
    def _parse_jwt_expiry(token: str) -> datetime:
        """
        Decode the ``exp`` claim from a JWT payload (no signature check).

        @param token  JWT string in the form ``header.payload.signature``.
        @return       Expiry as a UTC-aware :class:`datetime`.
                      Falls back to *now + 5 minutes* if parsing fails.
        """
        try:
            payload_b64 = token.split(".")[1]
            # Pad to a multiple of 4 for base64 decoding.
            padding = "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(
                base64.urlsafe_b64decode(payload_b64 + padding).decode()
            )
            return datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc) + timedelta(minutes=5)

    def _ensure_valid_token(self) -> None:
        """Refresh the access token if it is within the margin of expiry."""
        deadline = self._access_expires_at - timedelta(seconds=self._refresh_margin)
        if datetime.now(timezone.utc) >= deadline:
            self._do_refresh()

    def _do_refresh(self) -> None:
        """
        Use the refresh token to obtain a new access token.

        Falls back to full re-authentication if the refresh token itself
        has expired (HTTP 401).

        @raises AuthError  If re-authentication also fails.
        """
        url = f"{self._base_url}/auth/token/refresh/"
        try:
            resp = requests.post(
                url,
                json={"refresh": self._refresh_token},
                timeout=self._timeout,
            )
            if resp.status_code == 401:
                logger.warning("Refresh token expired — re-authenticating")
                self.authenticate()
                return
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise AuthError(
                f"Token refresh failed (HTTP {exc.response.status_code})"
            ) from exc
        except requests.RequestException as exc:
            raise AuthError(f"Token refresh request failed: {exc}") from exc

        data = resp.json()
        self._store_tokens(data["access"], self._refresh_token)
        logger.debug("Access token refreshed successfully")

    def _fetch_script_token(self) -> None:
        """
        Retrieve the ``script_token`` from the ``/auth/me/`` endpoint.

        Called automatically during :meth:`authenticate` when the token
        was not provided in the configuration file.

        @raises AuthError  If the token cannot be retrieved.
        """
        url = f"{self._base_url}/auth/me/"
        try:
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {self._access_token}"},
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise AuthError(f"Could not fetch script_token: {exc}") from exc

        token = resp.json().get("script_token", "")
        if not token:
            raise AuthError(
                "script_token is empty in /auth/me/ response and was not "
                "set in station_config.json."
            )
        self._script_token = token
        logger.info("Script token fetched from /auth/me/")
