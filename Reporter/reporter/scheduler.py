"""
@file   Reporter/reporter/scheduler.py
@brief  Single-threaded periodic scheduler for detection and upload cycles.

The :class:`Scheduler` runs two independent periodic tasks:

1. **Detection cycle** — calls :class:`~reporter.scanner.DetectionScanner`
   every ``scheduler.poll_interval_seconds`` seconds.
2. **Requirements cycle** — calls :class:`~reporter.uploader.RequirementUploader`
   every ``scheduler.requirements_poll_interval_seconds`` seconds.

Both tasks run in the same thread.  A :class:`threading.Event` is used for
graceful shutdown: calling :meth:`Scheduler.stop` wakes the sleeping loop
and the process exits cleanly.

On first boot the detection cycle runs immediately; subsequent runs are
delayed by the configured interval.  The requirements check is delayed by
one full interval before the first run.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from api.client import SkyEventsApiClient
from auth.client import AuthError
from config.models import StationReporterConfig
from state.tracker import StateTracker

from .scanner import DetectionScanner
from .uploader import RequirementUploader

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Periodic task runner for the SkyEvents Reporter.

    @param config         Full station configuration.
    @param api_client     Authenticated SkyEvents API client.
    @param state_tracker  Persistent state tracker.
    @param dry_run        Forward the dry-run flag to scanner and uploader.
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
        self._stop_event = threading.Event()
        self._scanner = DetectionScanner(config, api_client, state_tracker, dry_run)
        self._uploader = RequirementUploader(api_client, state_tracker, dry_run, config)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Start the scheduler loop and block until :meth:`stop` is called.

        The detection cycle runs immediately on the first iteration.
        The requirements cycle fires after the first full requirements
        interval has elapsed.
        The ping cycle fires immediately and then every ``ping_interval_seconds``.
        """
        poll = self._config.scheduler.poll_interval_seconds
        req_poll = self._config.scheduler.requirements_poll_interval_seconds
        ping_poll = self._config.scheduler.ping_interval_seconds

        logger.info(
            "Scheduler started — detection every %ds, requirements every %ds, ping every %ds",
            poll,
            req_poll,
            ping_poll,
        )

        next_detection = 0.0      # run immediately
        next_requirements = float(req_poll)  # first run after one interval
        next_ping = 0.0           # run immediately

        while not self._stop_event.is_set():
            now = datetime.now(tz=timezone.utc).timestamp()

            if now >= next_detection:
                self._run_detection_cycle()
                next_detection = datetime.now(tz=timezone.utc).timestamp() + poll

            if now >= next_requirements:
                self._run_requirements_cycle()
                next_requirements = datetime.now(tz=timezone.utc).timestamp() + req_poll

            if now >= next_ping:
                self._run_ping_cycle()
                next_ping = datetime.now(tz=timezone.utc).timestamp() + ping_poll

            # Sleep until the next scheduled task (or until stop is called).
            sleep_secs = min(
                next_detection - datetime.now(tz=timezone.utc).timestamp(),
                next_requirements - datetime.now(tz=timezone.utc).timestamp(),
                next_ping - datetime.now(tz=timezone.utc).timestamp(),
                poll,
            )
            sleep_secs = max(sleep_secs, 1.0)
            self._stop_event.wait(timeout=sleep_secs)

        logger.info("Scheduler stopped.")

    def run_once(self) -> None:
        """
        Run one detection cycle, one requirements cycle and one ping, then return.

        Useful for ``--once`` CLI mode or testing.
        """
        self._run_detection_cycle()
        self._run_requirements_cycle()
        self._run_ping_cycle()

    def stop(self) -> None:
        """Signal the scheduler to exit after the current sleep completes."""
        logger.info("Stop signal received.")
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Cycle helpers
    # ------------------------------------------------------------------

    def _run_detection_cycle(self) -> None:
        logger.info("--- Detection cycle starting ---")
        try:
            result = self._scanner.run_cycle()
            logger.info(
                "Detection cycle complete: %d created, %d skipped, %d errors",
                result.reports_created,
                result.reports_skipped,
                result.errors,
            )
        except AuthError as exc:
            logger.error("Authentication failure during detection cycle: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error in detection cycle: %s", exc, exc_info=True)

    def _run_requirements_cycle(self) -> None:
        logger.info("--- Requirements cycle starting ---")
        try:
            count = self._uploader.process()
            logger.info("Requirements cycle complete: %d file(s) uploaded", count)
        except AuthError as exc:
            logger.error("Authentication failure during requirements cycle: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected error in requirements cycle: %s", exc, exc_info=True
            )

    def _run_ping_cycle(self) -> None:
        logger.debug("--- Ping cycle ---")
        try:
            self._api.ping(self._config.station.hash_id)
            logger.debug("Ping sent for station %s", self._config.station.hash_id)
        except AuthError as exc:
            logger.warning("Authentication failure during ping: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ping failed: %s", exc)
