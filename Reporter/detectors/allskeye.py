"""
@file   Reporter/detectors/allskeye.py
@brief  Detector for AllSkyEye (allskyeye.com) detection CSV logs.

AllSkyEye writes a CSV detection log for each observing session.
The default filename pattern is ``Events_YYYYMMDD.csv``.  Each row
describes one meteor detection and may reference an associated video file.

Expected CSV column order (AllSkyEye ≥ 1.4):
    datetime, station_id, event_id, duration_s, peak_mag, ra, dec,
    azimuth, altitude, video_file, ...

Supported ``detector_options``:
  csv_pattern   (str)   Glob for detection CSV files.
                        Default: ``"Events_*.csv"``
  video_subdir  (str)   Subdirectory that holds the video files referenced
                        in the CSV.  Default: ``"Videos"``.
  delimiter     (str)   CSV field delimiter.  Default: ``","``
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils import guess_file_type

from .base import BaseDetector, DetectionEvent, DetectionFile

logger = logging.getLogger(__name__)

#: Column index of the datetime field in the AllSkyEye CSV.
_DT_COL = 0
#: Column index of the duration (seconds) field.
_DUR_COL = 3
#: Column index of the associated video file path.
_VIDEO_COL = 9

_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
)


def _parse_dt(value: str) -> datetime | None:
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class AllSkyEyeDetector(BaseDetector):
    """
    Detector adapter for AllSkyEye observation logs.

    Reads CSV event files produced by AllSkyEye and emits one
    :class:`DetectionEvent` per row, optionally including the
    referenced video file.

    @see BaseDetector for constructor parameters.
    """

    @property
    def name(self) -> str:
        return "AllSkyEye"

    def __init__(self, watch_path: str, options: dict[str, Any] | None = None) -> None:
        super().__init__(watch_path, options)
        self._csv_pattern: str = self.options.get("csv_pattern", "Events_*.csv")
        self._video_subdir: str = self.options.get("video_subdir", "Videos")
        self._delimiter: str = self.options.get("delimiter", ",")

    def scan(self, since: datetime | None = None) -> list[DetectionEvent]:
        """
        Parse AllSkyEye CSV logs for new detection rows.

        @param since  Only return events with timestamps after this value.
        @return       List of :class:`DetectionEvent` objects.
        """
        if not self.watch_path.exists():
            logger.warning("[%s] Watch path not found: %s", self.name, self.watch_path)
            return []

        video_dir = self.watch_path / self._video_subdir
        events: list[DetectionEvent] = []

        for csv_file in sorted(self.watch_path.glob(self._csv_pattern)):
            events.extend(self._parse_csv(csv_file, video_dir, since))

        events.sort(key=lambda e: e.detected_at)
        logger.debug("[%s] %d new event(s)", self.name, len(events))
        return events

    def _parse_csv(
        self, csv_path: Path, video_dir: Path, since: datetime | None
    ) -> list[DetectionEvent]:
        events: list[DetectionEvent] = []

        try:
            with csv_path.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.reader(fh, delimiter=self._delimiter)
                # Skip header row if present.
                first = next(reader, None)
                if first and not _parse_dt(first[_DT_COL] if first else ""):
                    pass  # header consumed; continue reading data rows
                else:
                    if first:
                        self._process_row(first, video_dir, since, events)

                for row in reader:
                    self._process_row(row, video_dir, since, events)
        except OSError as exc:
            logger.warning("[%s] Cannot read %s: %s", self.name, csv_path, exc)

        return events

    def _process_row(
        self,
        row: list[str],
        video_dir: Path,
        since: datetime | None,
        out: list[DetectionEvent],
    ) -> None:
        if len(row) <= _DT_COL:
            return

        dt = _parse_dt(row[_DT_COL])
        if dt is None:
            return
        if since is not None and dt <= since:
            return

        duration_ms: int | None = None
        if len(row) > _DUR_COL:
            try:
                duration_ms = int(float(row[_DUR_COL]) * 1000)
            except (ValueError, IndexError):
                pass

        detection_files: list[DetectionFile] = []
        if len(row) > _VIDEO_COL and row[_VIDEO_COL].strip():
            video_name = Path(row[_VIDEO_COL].strip()).name
            video_path = video_dir / video_name
            if video_path.exists():
                detection_files.append(
                    DetectionFile(
                        local_path=str(video_path.resolve()),
                        file_type="video",
                        file_size_bytes=video_path.stat().st_size,
                    )
                )

        out.append(DetectionEvent(detected_at=dt, files=detection_files, duration_ms=duration_ms))
