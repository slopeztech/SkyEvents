"""
@file   Reporter/detectors/meteordl.py
@brief  Detector for MeteorDL / CAMS-style event directories.

MeteorDL (and CAMS-derived software) saves each detection as a
subdirectory under the watch path:

    {STATION}_{YYYYMMDD_HHMMSS}_{NN}/
        event.xml         ← metadata (optional)
        detection.mp4     ← or *.avi / *.mkv
        detection.jpg     ← still frame

Directory names that follow the pattern
``{prefix}_{YYYYMMDD}_{HHMMSS}_{seq}`` are recognised.  Any event
directory whose name contains a parseable timestamp is also accepted.

Supported ``detector_options``:
  date_format (str)  strptime format string for the timestamp in the
                     directory name.  Default: ``"%Y%m%d_%H%M%S"``
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

# Matches: anything_YYYYMMDD_HHMMSS_anything  or  YYYYMMDD_HHMMSS_anything
_DT_RE = re.compile(r"(\d{8})_(\d{6})")


def _parse_dir_datetime(name: str) -> datetime | None:
    """
    Extract the first ``YYYYMMDD_HHMMSS`` timestamp found in *name*.

    @param name  Directory name string.
    @return      UTC-aware :class:`datetime`, or ``None``.
    """
    m = _DT_RE.search(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


class MeteorDLDetector(BaseDetector):
    """
    Detector adapter for MeteorDL / CAMS event-directory layout.

    One subdirectory = one detection event.

    @see BaseDetector for constructor parameters.
    """

    @property
    def name(self) -> str:
        return "MeteorDL"

    def scan(self, since: datetime | None = None) -> list[DetectionEvent]:
        """
        Scan the watch directory for new event subdirectories.

        @param since  Exclude events with a timestamp ≤ this value.
        @return       One :class:`DetectionEvent` per recognised directory.
        """
        if not self.watch_path.exists():
            logger.warning("[%s] Watch path not found: %s", self.name, self.watch_path)
            return []

        events: list[DetectionEvent] = []

        for event_dir in sorted(self.watch_path.iterdir()):
            if not event_dir.is_dir():
                continue

            dt = _parse_dir_datetime(event_dir.name)
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
