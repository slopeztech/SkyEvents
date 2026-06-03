"""
@file   Reporter/detectors/rms.py
@brief  Detector for RMS (Raspberry Meteor Station) archived captures.

RMS (by the Croatian Meteor Network, Denis Vida et al.) creates one
subdirectory per captured detection inside ``ArchivedFiles/``:

    {STATION}_{YYYYMMDD}_{HHMMSS}_{ENDSEC}/
        {STATION}_{YYYYMMDD}_{HHMMSS}_{ENDSEC}.mp4        ← detection video
        {STATION}_{YYYYMMDD}_{HHMMSS}_{ENDSEC}_stack.jpg  ← stacked image
        FTPdetectinfo_{STATION}_{YYYYMMDD}_{HHMMSS}_{ENDSEC}.txt  ← metadata
        *.fits                                             ← individual frames

Each directory maps to one :class:`DetectionEvent`.

Supported ``detector_options``:
  station_code (str)   Expected station code prefix (e.g. ``HR0001``).
                       If supplied, only directories matching that prefix
                       are processed.
  subdir       (str)   Subdirectory inside watch_path to scan.
                       Default: ``"ArchivedFiles"``.  Set to ``""`` to scan
                       the watch_path directly.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils import guess_file_type

from .base import BaseDetector, DetectionEvent, DetectionFile

logger = logging.getLogger(__name__)

# RMS archived directory name: STATION_YYYYMMDD_HHMMSS_ENDSEC
_RMS_DIR_RE = re.compile(r"^([A-Z0-9]+)_(\d{8})_(\d{6})_\d+$", re.IGNORECASE)


def _parse_rms_datetime(name: str) -> datetime | None:
    """
    Parse the UTC start timestamp from an RMS archived directory name.

    @param name  Directory name (e.g. ``HR0001_20240815_223015_123456``).
    @return      UTC-aware :class:`datetime`, or ``None`` on failure.
    """
    m = _RMS_DIR_RE.match(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(2) + m.group(3), "%Y%m%d%H%M%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


class RMSDetector(BaseDetector):
    """
    Detector adapter for RMS (Raspberry Meteor Station).

    Scans the ``ArchivedFiles/`` subdirectory (configurable) for event
    directories and collects all files inside each one.

    @see BaseDetector for constructor parameters.
    """

    @property
    def name(self) -> str:
        return "RMS"

    def __init__(self, watch_path: str, options: dict[str, Any] | None = None) -> None:
        super().__init__(watch_path, options)
        self._station_code: str = self.options.get("station_code", "").upper()
        subdir: str = self.options.get("subdir", "ArchivedFiles")
        self._archive_path: Path = (
            self.watch_path / subdir if subdir else self.watch_path
        )

    def scan(self, since: datetime | None = None) -> list[DetectionEvent]:
        """
        Scan the RMS archive directory for new event folders.

        @param since  Exclude events with a timestamp ≤ this value.
        @return       One :class:`DetectionEvent` per archived event directory.
        """
        if not self._archive_path.exists():
            logger.warning("[%s] Archive path not found: %s", self.name, self._archive_path)
            return []

        events: list[DetectionEvent] = []

        for event_dir in sorted(self._archive_path.iterdir()):
            if not event_dir.is_dir():
                continue
            if self._station_code and not event_dir.name.upper().startswith(
                self._station_code
            ):
                continue

            dt = _parse_rms_datetime(event_dir.name)
            if dt is None:
                continue
            if since is not None and dt <= since:
                continue

            detection_files = [
                DetectionFile(
                    local_path=str(fp.resolve()),
                    file_type=guess_file_type(fp),
                    file_size_bytes=fp.stat().st_size,
                )
                for fp in sorted(event_dir.iterdir())
                if fp.is_file()
            ]

            if not detection_files:
                continue

            events.append(DetectionEvent(detected_at=dt, files=detection_files))

        events.sort(key=lambda e: e.detected_at)
        logger.debug("[%s] %d new event(s)", self.name, len(events))
        return events
