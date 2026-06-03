"""
@file   Reporter/reporter/uploader.py
@brief  Uploads pending files requested by the SkyEvents requirements endpoint.

The :class:`RequirementUploader` polls ``GET /api/v1/station/requirements/``
for open requirements (files that the server is requesting from the station).
For each requirement it checks whether the file exists locally and has not
already been uploaded, then uploads it via
``POST /api/v1/station/requirements/{uuid}/media/``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from api.client import ApiError, SkyEventsApiClient
from state.tracker import StateTracker
from utils import guess_file_type

if TYPE_CHECKING:
    from config.models import StationReporterConfig

logger = logging.getLogger(__name__)


class RequirementUploader:
    """
    Handles uploading locally available files requested by the server.

    A *requirement* is a server-side record indicating that the station
    should upload a specific file (identified by its path/name on the
    station storage).  The server returns each requirement with a
    ``requested_paths`` list (one filename/path per entry).

    Resolution order for each entry in ``requested_paths``:
    1. Use the path as-is if it is absolute and the file exists.
    2. Search in every device ``watch_path`` (and its subdirectories)
       for a file whose name matches.

    @param api_client    Authenticated SkyEvents API client.
    @param state_tracker Persistent state tracker.
    @param dry_run       If ``True``, logs actions without calling the API.
    @param config        Full station config; used to resolve watch_paths.
    """

    def __init__(
        self,
        api_client: SkyEventsApiClient,
        state_tracker: StateTracker,
        dry_run: bool = False,
        config: "StationReporterConfig | None" = None,
    ) -> None:
        self._api = api_client
        self._state = state_tracker
        self._dry_run = dry_run
        self._watch_paths: list[Path] = []
        if config is not None:
            for dev in list(config.devices.cameras) + list(config.devices.radios):
                wp = Path(dev.watch_path)
                if wp not in self._watch_paths:
                    self._watch_paths.append(wp)

    def process(self) -> int:
        """
        Fetch open requirements and upload any available local files.

        @return  Number of files successfully uploaded in this call.
        """
        try:
            requirements = self._api.list_requirements()
        except ApiError as exc:
            logger.error("Could not fetch requirements: %s", exc)
            return 0

        if not requirements:
            logger.debug("No open requirements.")
            return 0

        uploaded = 0
        for req in requirements:
            uploaded += self._process_requirement(req)

        return uploaded

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, name_or_path: str) -> Path | None:
        """
        Resolve a filename or path from the requirement to a local Path.

        Tries, in order:
        1. The value as an absolute (or relative-to-cwd) path.
        2. A file with that basename found under any configured watch_path.

        @param name_or_path  Filename or path string from ``requested_paths``.
        @return              Resolved :class:`Path` if found locally, else ``None``.
        """
        candidate = Path(name_or_path)
        if candidate.exists():
            return candidate

        # Search watch paths by filename match (non-recursive first, then recursive).
        target_name = candidate.name
        for watch_dir in self._watch_paths:
            if not watch_dir.is_dir():
                continue
            # Non-recursive: direct children
            direct = watch_dir / target_name
            if direct.exists():
                return direct
            # Recursive: search subdirectories
            for found in watch_dir.rglob(target_name):
                return found  # return first match

        return None

    def _process_requirement(self, req: dict) -> int:
        """
        Attempt to upload all files requested by a single requirement.

        The requirement dict must contain:
        - ``id``               (str)   UUID of the requirement.
        - ``requested_paths``  (list)  Filenames / paths on the station storage.

        @param req  Requirement dict from the API.
        @return     Number of files successfully uploaded.
        """
        req_id: str = req.get("id", "")
        requested_paths: list = req.get("requested_paths") or []

        if not req_id:
            logger.warning("Requirement missing 'id': %s", req)
            return 0

        if not requested_paths:
            logger.warning("Requirement %s has empty 'requested_paths'", req_id)
            return 0

        uploaded = 0
        for path_str in requested_paths:
            uploaded += self._upload_one(req_id, path_str)
        return uploaded

    def _upload_one(self, req_id: str, path_str: str) -> int:
        """Upload a single file entry from a requirement."""
        file_path = self._resolve_path(path_str)

        if file_path is None:
            logger.warning(
                "Requirement %s: file not found locally: %s (searched watch_paths: %s)",
                req_id,
                path_str,
                [str(p) for p in self._watch_paths],
            )
            return 0

        if self._state.is_uploaded(str(file_path), req_id):
            logger.debug("Requirement %s already uploaded: %s", req_id, file_path)
            return 0

        file_type = guess_file_type(file_path)

        if self._dry_run:
            logger.info(
                "[dry-run] Would upload %s (type=%s) for requirement %s",
                file_path,
                file_type,
                req_id,
            )
            self._state.mark_uploaded(str(file_path), req_id)
            return 1

        try:
            self._api.upload_attachment(
                requirement_id=req_id,
                file_path=file_path,
                original_path=path_str,
                file_type=file_type,
            )
            self._state.mark_uploaded(str(file_path), req_id)
            logger.info(
                "Uploaded %s for requirement %s", file_path.name, req_id
            )
            return 1
        except ApiError as exc:
            logger.error(
                "Failed to upload %s for requirement %s: %s",
                file_path.name,
                req_id,
                exc,
            )
            return 0
