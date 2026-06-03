"""
@file   Reporter/detectors/base.py
@brief  Abstract base class and shared data models for all detectors.

Every capture-software adapter must subclass :class:`BaseDetector` and
implement :meth:`BaseDetector.scan`.  The return type is always a list
of :class:`DetectionEvent` objects, which are software-agnostic and can
be fed directly into the report builder.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data models (software-agnostic)
# ---------------------------------------------------------------------------


@dataclass
class DetectionFile:
    """
    Metadata for a single file produced by a detection event.

    @var local_path       Absolute path to the file on the station filesystem.
    @var file_type        SkyEvents file type: ``video``, ``image``,
                          ``spectrogram``, ``audio``, ``data``, or ``other``.
    @var file_size_bytes  File size in bytes, or ``None`` if unknown.
    @var description      Optional free-text description.
    """

    local_path: str
    file_type: str
    file_size_bytes: int | None = None
    description: str = ""


@dataclass
class DetectionEvent:
    """
    A single astronomical detection event as reported by the capture software.

    @var detected_at  UTC timestamp of the detection onset.
    @var files        Files associated with the event (video, images, data).
    @var duration_ms  Detection duration in milliseconds, or ``None``.
    @var notes        Free-text notes extracted from the capture software.
    """

    detected_at: datetime
    files: list[DetectionFile] = field(default_factory=list)
    duration_ms: int | None = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Abstract detector
# ---------------------------------------------------------------------------


class BaseDetector(ABC):
    """
    Abstract adapter for a specific meteor-capture software.

    Subclasses parse the watch directory and return :class:`DetectionEvent`
    objects that are software-agnostic.  The scheduler calls :meth:`scan`
    periodically; only events newer than *since* should be returned.

    @var watch_path  Directory that this detector is configured to scan.
    @var options     Free-form options dict from ``detector_options`` in the
                     station config (e.g. station code, file pattern, …).
    """

    def __init__(self, watch_path: str, options: dict[str, Any] | None = None) -> None:
        self.watch_path = Path(watch_path)
        self.options: dict[str, Any] = options or {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the detector (e.g. ``"UFOCapture"``)."""

    @abstractmethod
    def scan(self, since: datetime | None = None) -> list[DetectionEvent]:
        """
        Scan :attr:`watch_path` for detection events.

        @param since  If provided, only events with a timestamp strictly
                      newer than this value should be returned.
                      Pass ``None`` on the first run to retrieve all events.
        @return       List of :class:`DetectionEvent` objects, sorted by
                      ``detected_at`` ascending.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} path={self.watch_path}>"
