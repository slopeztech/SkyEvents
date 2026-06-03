"""
@file   Reporter/reporter/builder.py
@brief  Converts a :class:`DetectionEvent` into a SkyEvents API payload dict.

The :class:`ReportBuilder` is the single translation layer between the
detector-agnostic :class:`~detectors.base.DetectionEvent` model and the
JSON payload expected by the SkyEvents ``POST /api/v1/station/reports/``
endpoint.

Report payload shape (mirrors the DRF serializer)::

    {
        "station_hash_id": "<station_hash_id>",
        "camera_hash_id": "<camera_hash_id>",   // omitted if empty
        "radio_hash_id":  "<radio_hash_id>",    // omitted if empty
        "recorded_at": "<ISO-8601 UTC>",
        "duration_ms": <int|null>,
        "notes": "<str>",
        "files": [
            {
                "file_type": "<str>",
                "filename": "<str>",
                "file_size_bytes": <int|null>,
                "description": "<str>"
            },
            ...
        ]
    }
"""

from __future__ import annotations

from pathlib import Path

from detectors.base import DetectionEvent


class ReportBuilder:
    """
    Builds SkyEvents API report payloads from :class:`DetectionEvent` objects.

    All constructor parameters are station / device identifiers that are
    injected into every report produced by this builder instance.

    @param station_hash_id  Hash ID of the reporting station.
    @param camera_hash_id   Hash ID of the camera device (empty string if N/A).
    @param radio_hash_id    Hash ID of the radio device (empty string if N/A).
    """

    def __init__(
        self,
        station_hash_id: str,
        camera_hash_id: str = "",
        radio_hash_id: str = "",
    ) -> None:
        self._station = station_hash_id
        self._camera = camera_hash_id
        self._radio = radio_hash_id

    def build(self, event: DetectionEvent) -> dict:
        """
        Convert *event* into a dict suitable for the reports endpoint.

        @param event  The detection event to convert.
        @return       JSON-serialisable dict matching the API payload schema.
        """
        payload: dict = {
            "station_hash_id": self._station,
            "recorded_at": event.detected_at.isoformat(),
            "notes": event.notes or "",
            "files": [
                {
                    "file_type": df.file_type,
                    "filename": Path(df.local_path).name,
                    "file_size_bytes": df.file_size_bytes,
                    "description": df.description or "",
                }
                for df in event.files
            ],
        }

        if event.duration_ms is not None:
            payload["duration_ms"] = event.duration_ms

        if self._camera:
            payload["camera_hash_id"] = self._camera

        if self._radio:
            payload["radio_hash_id"] = self._radio

        return payload
