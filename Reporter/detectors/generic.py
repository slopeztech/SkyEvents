"""
@file   Reporter/detectors/generic.py
@brief  Generic directory-watcher detector.

Watches a folder for new files matching a configurable glob pattern.
Each matching file becomes its own :class:`DetectionEvent`.  Use this
adapter when no dedicated detector exists for your capture software.

Supported ``detector_options``:
  pattern   (str)   Glob pattern to match.  Default: ``"*.mp4"``
  recursive (bool)  If true, recurse into subdirectories.  Default: false.
  file_type (str)   Force a specific SkyEvents ``file_type`` for all matched
                    files.  If omitted the type is inferred from the extension.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils import guess_file_type

from .base import BaseDetector, DetectionEvent, DetectionFile

logger = logging.getLogger(__name__)


class GenericDetector(BaseDetector):
    """
    Watches a directory for new files that match a glob pattern.

    Each matched file is wrapped in a single :class:`DetectionEvent`.  The
    event timestamp is taken from the file's last-modified time (``mtime``).

    This detector is a useful fallback for any capture software that simply
    writes detection files to a folder without a specific metadata format.

    @see BaseDetector for parameter documentation.
    """

    @property
    def name(self) -> str:
        return "Generic"

    def __init__(self, watch_path: str, options: dict[str, Any] | None = None) -> None:
        super().__init__(watch_path, options)
        self._pattern: str = self.options.get("pattern", "*.mp4")
        self._recursive: bool = bool(self.options.get("recursive", False))
        self._forced_type: str = self.options.get("file_type", "")

    def scan(self, since: datetime | None = None) -> list[DetectionEvent]:
        """
        Find files matching :attr:`_pattern` that were modified after *since*.

        @param since  Only return events with mtime strictly after this value.
        @return       One :class:`DetectionEvent` per matching file.
        """
        if not self.watch_path.exists():
            logger.warning(
                "[%s] Watch path does not exist: %s", self.name, self.watch_path
            )
            return []

        glob_fn = self.watch_path.rglob if self._recursive else self.watch_path.glob
        events: list[DetectionEvent] = []

        for fpath in sorted(glob_fn(self._pattern)):
            if not fpath.is_file():
                continue

            mtime = datetime.fromtimestamp(fpath.stat().st_mtime, tz=timezone.utc)
            if since is not None and mtime <= since:
                continue

            file_type = self._forced_type or guess_file_type(fpath)
            df = DetectionFile(
                local_path=str(fpath.resolve()),
                file_type=file_type,
                file_size_bytes=fpath.stat().st_size,
            )
            events.append(DetectionEvent(detected_at=mtime, files=[df]))

        logger.debug("[%s] %d new file(s) found in %s", self.name, len(events), self.watch_path)
        return events
