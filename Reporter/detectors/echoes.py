"""
@file   Reporter/detectors/echoes.py
@brief  Detector for Echoes (radio forward-scatter) observation CSV files.

Echoes (by Felix Verbelen) saves radio-meteor detections in CSV files
and optionally produces spectrogram images.  The default observation log
is ``echoes_YYYYMMDD.csv`` with one row per detection.

Expected CSV column order (Echoes ≥ 2.0):
    date_utc, time_utc, duration_s, max_power_db, freq_hz,
    spectrogram_file, ...

If a ``spectrogram_file`` column is present and the referenced ``.png``
exists, it is attached to the event as a spectrogram file.

Supported ``detector_options``:
  csv_pattern   (str)   Glob for Echoes observation CSV files.
                        Default: ``"echoes_*.csv"``
  spec_subdir   (str)   Subdirectory containing spectrogram images.
                        Default: ``""`` (same directory as the CSV).
  delimiter     (str)   CSV field delimiter.  Default: ``","``
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import BaseDetector, DetectionEvent, DetectionFile

logger = logging.getLogger(__name__)

# Column indices for Echoes CSV.
_COL_DATE = 0
_COL_TIME = 1
_COL_DUR = 2
_COL_SPEC = 5  # spectrogram filename (may not always be present)

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
)


def _parse_echoes_dt(date_val: str, time_val: str) -> datetime | None:
    combined = f"{date_val.strip()} {time_val.strip()}"
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(combined, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class EchoesDetector(BaseDetector):
    """
    Detector adapter for Echoes radio-meteor observation logs.

    Reads Echoes CSV log files and emits one :class:`DetectionEvent` per
    row, attaching spectrogram images where available.

    @see BaseDetector for constructor parameters.
    """

    @property
    def name(self) -> str:
        return "Echoes"

    def __init__(self, watch_path: str, options: dict[str, Any] | None = None) -> None:
        super().__init__(watch_path, options)
        self._csv_pattern: str = self.options.get("csv_pattern", "echoes_*.csv")
        self._spec_subdir: str = self.options.get("spec_subdir", "")
        self._delimiter: str = self.options.get("delimiter", ",")

    def scan(self, since: datetime | None = None) -> list[DetectionEvent]:
        """
        Parse Echoes CSV logs for new detection rows.

        @param since  Only return events with timestamps after this value.
        @return       List of :class:`DetectionEvent` objects.
        """
        if not self.watch_path.exists():
            logger.warning("[%s] Watch path not found: %s", self.name, self.watch_path)
            return []

        spec_dir = (
            self.watch_path / self._spec_subdir
            if self._spec_subdir
            else self.watch_path
        )
        events: list[DetectionEvent] = []

        for csv_file in sorted(self.watch_path.glob(self._csv_pattern)):
            # Skip files not modified since last scan.
            if since is not None:
                mtime = datetime.fromtimestamp(
                    csv_file.stat().st_mtime, tz=timezone.utc
                )
                if mtime <= since:
                    continue
            events.extend(self._parse_csv(csv_file, spec_dir, since))

        events.sort(key=lambda e: e.detected_at)
        logger.debug("[%s] %d new event(s)", self.name, len(events))
        return events

    def _parse_csv(
        self, csv_path: Path, spec_dir: Path, since: datetime | None
    ) -> list[DetectionEvent]:
        events: list[DetectionEvent] = []
        try:
            with csv_path.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.reader(fh, delimiter=self._delimiter)
                for row in reader:
                    if len(row) < 2:
                        continue
                    event = self._process_row(row, spec_dir, since)
                    if event is not None:
                        events.append(event)
        except OSError as exc:
            logger.warning("[%s] Cannot read %s: %s", self.name, csv_path, exc)
        return events

    def _process_row(
        self,
        row: list[str],
        spec_dir: Path,
        since: datetime | None,
    ) -> DetectionEvent | None:
        dt = _parse_echoes_dt(row[_COL_DATE], row[_COL_TIME] if len(row) > _COL_TIME else "")
        if dt is None:
            return None
        if since is not None and dt <= since:
            return None

        duration_ms: int | None = None
        if len(row) > _COL_DUR:
            try:
                duration_ms = int(float(row[_COL_DUR]) * 1000)
            except (ValueError, IndexError):
                pass

        detection_files: list[DetectionFile] = []
        if len(row) > _COL_SPEC and row[_COL_SPEC].strip():
            spec_name = Path(row[_COL_SPEC].strip()).name
            spec_path = spec_dir / spec_name
            if not spec_path.exists():
                # Try with .png extension if not found by given name.
                spec_path = spec_dir / (Path(spec_name).stem + ".png")
            if spec_path.exists():
                detection_files.append(
                    DetectionFile(
                        local_path=str(spec_path.resolve()),
                        file_type="spectrogram",
                        file_size_bytes=spec_path.stat().st_size,
                        description="Echoes spectrogram",
                    )
                )

        return DetectionEvent(
            detected_at=dt,
            files=detection_files,
            duration_ms=duration_ms,
        )
