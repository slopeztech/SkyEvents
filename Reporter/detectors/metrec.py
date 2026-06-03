"""
@file   Reporter/detectors/metrec.py
@brief  Detector for MetRec (Sirko Molau) ``.met`` ASCII observation files.

MetRec writes one ``.met`` ASCII file per night / session containing all
detected meteors in a fixed-format text record.  Each record starts with
a line beginning ``Meteor`` followed by fields including the UT date and
start time.

MetRec ``.met`` file format (simplified):

    Meteor          ← record marker
    Date: 20240815
    Time: 22:30:15.4
    Duration: 2.3
    ...             ← additional metadata lines
    EndMeteor       ← end of record

The ``watch_path`` is scanned for ``*.met`` files.  Modification-time
filtering is applied to the file itself; individual records within an
already-processed file are skipped if their parsed timestamp ≤ *since*.

Supported ``detector_options``:
  file_pattern (str)  Glob pattern for MetRec data files.
                      Default: ``"*.met"``
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import BaseDetector, DetectionEvent, DetectionFile

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"^\s*Date\s*[:\s]\s*(\d{8})", re.IGNORECASE)
_TIME_RE = re.compile(r"^\s*Time\s*[:\s]\s*(\d{1,2}:\d{2}:\d{2})", re.IGNORECASE)
_DUR_RE = re.compile(r"^\s*Duration\s*[:\s]\s*([\d.]+)", re.IGNORECASE)


def _parse_met_file(met_path: Path, since: datetime | None) -> list[DetectionEvent]:
    """
    Parse a MetRec ``.met`` file and return :class:`DetectionEvent` objects.

    @param met_path  Path to the ``.met`` file.
    @param since     Skip records whose timestamp ≤ this value.
    @return          List of detection events extracted from the file.
    """
    events: list[DetectionEvent] = []
    in_record = False
    date_str = ""
    time_str = ""
    duration_s: float | None = None

    def _flush() -> None:
        nonlocal date_str, time_str, duration_s
        if not (date_str and time_str):
            date_str = time_str = ""
            duration_s = None
            return
        try:
            dt = datetime.strptime(
                f"{date_str} {time_str}", "%Y%m%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            date_str = time_str = ""
            duration_s = None
            return

        if since is None or dt > since:
            dur_ms = int(duration_s * 1000) if duration_s is not None else None
            events.append(
                DetectionEvent(
                    detected_at=dt,
                    duration_ms=dur_ms,
                    notes=f"Source: {met_path.name}",
                )
            )
        date_str = time_str = ""
        duration_s = None

    try:
        lines = met_path.read_text(encoding="latin-1", errors="replace").splitlines()
    except OSError as exc:
        logger.warning("[MetRec] Cannot read %s: %s", met_path, exc)
        return []

    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("meteor") and not stripped.lower().startswith(
            "endmeteor"
        ):
            in_record = True
            date_str = time_str = ""
            duration_s = None
            continue

        if stripped.lower().startswith("endmeteor"):
            if in_record:
                _flush()
            in_record = False
            continue

        if not in_record:
            continue

        m = _DATE_RE.match(stripped)
        if m:
            date_str = m.group(1)
            continue

        m = _TIME_RE.match(stripped)
        if m:
            time_str = m.group(1)
            continue

        m = _DUR_RE.match(stripped)
        if m:
            try:
                duration_s = float(m.group(1))
            except ValueError:
                pass

    return events


class MetRecDetector(BaseDetector):
    """
    Detector adapter for MetRec ASCII ``.met`` observation files.

    Scans the watch directory for ``.met`` files and parses each one,
    yielding one :class:`DetectionEvent` per meteor record.

    @see BaseDetector for constructor parameters.
    """

    @property
    def name(self) -> str:
        return "MetRec"

    def __init__(self, watch_path: str, options: dict[str, Any] | None = None) -> None:
        super().__init__(watch_path, options)
        self._file_pattern: str = self.options.get("file_pattern", "*.met")

    def scan(self, since: datetime | None = None) -> list[DetectionEvent]:
        """
        Parse MetRec ``.met`` files for new meteor records.

        Only files modified after *since* (using mtime) are re-parsed,
        then individual records are filtered by timestamp.

        @param since  Exclude records with a timestamp ≤ this value.
        @return       List of :class:`DetectionEvent` objects.
        """
        if not self.watch_path.exists():
            logger.warning("[%s] Watch path not found: %s", self.name, self.watch_path)
            return []

        events: list[DetectionEvent] = []
        for met_file in sorted(self.watch_path.glob(self._file_pattern)):
            if not met_file.is_file():
                continue
            # Skip files that haven't been modified since the last scan.
            if since is not None:
                mtime = datetime.fromtimestamp(
                    met_file.stat().st_mtime, tz=timezone.utc
                )
                if mtime <= since:
                    continue
            events.extend(_parse_met_file(met_file, since))

        events.sort(key=lambda e: e.detected_at)
        logger.debug("[%s] %d new record(s)", self.name, len(events))
        return events
