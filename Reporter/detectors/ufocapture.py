"""
@file   Reporter/detectors/ufocapture.py
@brief  Detector for UFOCapture / UFOCaptureHD2 (SonotaCo) output files.

UFOCapture (Windows, by SonotaCo) writes one set of files per detected
meteor into a flat directory (or configurable date subdirectories):

    M{YYYYMMDD}_{HHMMSS}_{StationCode}_{NN}.avi    ← detection video
    M{YYYYMMDD}_{HHMMSS}_{StationCode}_{NN}.jpg    ← composite image
    M{YYYYMMDD}_{HHMMSS}_{StationCode}_{NN}.xml    ← detection metadata (optional)
    A{YYYYMMDD}_{HHMMSS}_{StationCode}_{NN}.bmp    ← analysis image (optional)

Files sharing the same base name (prefix + station + camera number) belong
to the same detection event.  The timestamp is parsed from the filename.

Supported ``detector_options``:
  date_subfolders (bool)  If true, scans one level of date-named subdirectories
                          (``YYYYMMDD/``) inside the watch path.  Default: false.
  extensions      (list)  Extensions to collect per event.
                          Default: ``[".avi", ".jpg", ".xml", ".bmp"]``
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils import guess_file_type

from .base import BaseDetector, DetectionEvent, DetectionFile

logger = logging.getLogger(__name__)

# Regex for UFOCapture filenames: M20240815_223015_HR0001_01
_UFOCAP_RE = re.compile(
    r"^[MA](\d{8})_(\d{6})_[^_]+_\d+$", re.IGNORECASE
)


def _parse_ufocap_datetime(stem: str) -> datetime | None:
    """
    Parse the UTC datetime embedded in a UFOCapture filename stem.

    @param stem  File stem without extension (e.g. ``M20240815_223015_HR0001_01``).
    @return      UTC-aware :class:`datetime`, or ``None`` if parsing fails.
    """
    m = _UFOCAP_RE.match(stem)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


class UFOCaptureDetector(BaseDetector):
    """
    Detector adapter for UFOCapture / UFOCaptureHD2.

    Groups all files that share the same base name into one
    :class:`DetectionEvent`.

    @see BaseDetector for constructor parameters.
    """

    @property
    def name(self) -> str:
        return "UFOCapture"

    def __init__(self, watch_path: str, options: dict[str, Any] | None = None) -> None:
        super().__init__(watch_path, options)
        self._date_subfolders: bool = bool(self.options.get("date_subfolders", False))
        self._extensions: set[str] = {
            ext.lower()
            for ext in self.options.get("extensions", [".avi", ".jpg", ".xml", ".bmp"])
        }

    def scan(self, since: datetime | None = None) -> list[DetectionEvent]:
        """
        Scan for new UFOCapture detection events.

        Files are grouped by their base name; the event timestamp is
        extracted from the filename.

        @param since  Exclude events with a timestamp ≤ this value.
        @return       List of :class:`DetectionEvent`, sorted by time.
        """
        if not self.watch_path.exists():
            logger.warning("[%s] Watch path not found: %s", self.name, self.watch_path)
            return []

        search_dirs: list[Path] = self._resolve_search_dirs()

        # Group files by base name (everything before the extension).
        groups: dict[str, list[Path]] = defaultdict(list)
        for search_dir in search_dirs:
            for fpath in search_dir.iterdir():
                if not fpath.is_file():
                    continue
                if fpath.suffix.lower() not in self._extensions:
                    continue
                if not _UFOCAP_RE.match(fpath.stem):
                    continue
                groups[fpath.stem].append(fpath)

        events: list[DetectionEvent] = []
        for stem, files in groups.items():
            dt = _parse_ufocap_datetime(stem)
            if dt is None:
                logger.debug("[%s] Could not parse timestamp from: %s", self.name, stem)
                continue
            if since is not None and dt <= since:
                continue

            detection_files = [
                DetectionFile(
                    local_path=str(fp.resolve()),
                    file_type=guess_file_type(fp),
                    file_size_bytes=fp.stat().st_size,
                )
                for fp in sorted(files, key=lambda p: p.suffix)
            ]
            events.append(DetectionEvent(detected_at=dt, files=detection_files))

        events.sort(key=lambda e: e.detected_at)
        logger.debug("[%s] %d new event(s)", self.name, len(events))
        return events

    def _resolve_search_dirs(self) -> list[Path]:
        if not self._date_subfolders:
            return [self.watch_path]
        return [d for d in self.watch_path.iterdir() if d.is_dir()]
