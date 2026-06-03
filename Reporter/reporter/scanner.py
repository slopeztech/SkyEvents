"""
@file   Reporter/reporter/scanner.py
@brief  Orchestrates per-device detection scanning and report submission.

The :class:`DetectionScanner` iterates over all configured devices,
creates the appropriate detector via the registry, calls ``scan(since=…)``,
filters already-processed files, submits new reports through the API, and
updates the state tracker.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import NamedTuple

from api.client import ApiError, SkyEventsApiClient
from config.models import DeviceConfig, StationReporterConfig
from detectors.base import DetectionEvent, DetectionFile
from detectors.registry import create_detector
from state.tracker import StateTracker

from .builder import ReportBuilder

logger = logging.getLogger(__name__)


class ScanResult(NamedTuple):
    """Summary returned after scanning all devices in one cycle."""

    reports_created: int
    reports_skipped: int
    errors: int


class DetectionScanner:
    """
    Scans all configured devices for new detections and submits reports.

    @param config        Full station configuration.
    @param api_client    Authenticated SkyEvents API client.
    @param state_tracker Persistent state tracker.
    @param dry_run       If ``True``, detects events but does not call the API.
    """

    def __init__(
        self,
        config: StationReporterConfig,
        api_client: SkyEventsApiClient,
        state_tracker: StateTracker,
        dry_run: bool = False,
    ) -> None:
        self._config = config
        self._api = api_client
        self._state = state_tracker
        self._dry_run = dry_run

    def run_cycle(self) -> ScanResult:
        """
        Execute one full detection cycle across all devices.

        @return  A :class:`ScanResult` with counts of created / skipped
                 reports and any per-device errors.
        """
        created = skipped = errors = 0

        for device_type, device in self._config.devices.all_devices:
            try:
                c, s = self._scan_device(device_type, device)
                created += c
                skipped += s
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Error scanning device '%s' (%s): %s",
                    device.name,
                    device.hash_id,
                    exc,
                    exc_info=True,
                )
                errors += 1

        return ScanResult(created, skipped, errors)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scan_device(self, device_type: str, device: DeviceConfig) -> tuple[int, int]:
        """
        Scan a single device and submit any new reports.

        @param device_type  ``"camera"`` or ``"radio"``.
        @param device       Device configuration object.
        @return             Tuple of (reports_created, reports_skipped).
        """
        since = self._state.get_last_scan_time(device.hash_id)
        logger.info(
            "Scanning device '%s' [%s] since %s",
            device.name,
            device.detector,
            since.isoformat() if since else "beginning",
        )

        detector = create_detector(device.detector, device.watch_path, device.detector_options)
        events = detector.scan(since=since)

        max_files = self._config.scheduler.max_files_per_cycle
        if len(events) > max_files:
            logger.warning(
                "Device '%s': %d events found, capping at %d per cycle.",
                device.name,
                len(events),
                max_files,
            )
            events = events[:max_files]

        created = skipped = 0
        builder = self._make_builder(device_type, device)

        for event in events:
            c, s = self._submit_event(event, device, builder)
            created += c
            skipped += s

        # Advance the scan timestamp to now (even if no events were found).
        self._state.set_last_scan_time(device.hash_id, datetime.now(tz=timezone.utc))
        return created, skipped

    def _submit_event(
        self, event: DetectionEvent, device: DeviceConfig, builder: ReportBuilder
    ) -> tuple[int, int]:
        """
        Submit a single detection event as a report.

        If all files in the event have already been processed, the event is
        skipped.  Partial duplicates (some files processed, some not) are
        still submitted because the report may not have been fully recorded.

        @return  Tuple of (created, skipped).
        """
        all_files: list[DetectionFile] = event.files

        if all_files and all(
            self._state.is_file_processed(df.local_path) for df in all_files
        ):
            logger.debug("Skipping already-processed event at %s", event.detected_at)
            return 0, 1

        payload = builder.build(event)

        if self._dry_run:
            logger.info("[dry-run] Would submit report: %s", payload.get("detected_at"))
            for df in all_files:
                self._state.mark_file_processed(df.local_path, "dry-run")
            return 1, 0

        try:
            result = self._api.create_report(payload)
            report_id: str = result.get("id", "")
            for df in all_files:
                self._state.mark_file_processed(df.local_path, report_id)
            logger.info("Report created: %s (device: %s)", report_id, device.name)
            return 1, 0
        except ApiError as exc:
            logger.error("API error submitting report: %s", exc)
            return 0, 0

    def _make_builder(self, device_type: str, device: DeviceConfig) -> ReportBuilder:
        station_id = self._config.station.hash_id
        camera_id = device.hash_id if device_type == "camera" else ""
        radio_id = device.hash_id if device_type == "radio" else ""
        return ReportBuilder(station_id, camera_id, radio_id)
