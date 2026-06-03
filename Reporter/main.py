"""
@file   Reporter/main.py
@brief  Entry point for the SkyEvents Reporter station script.

Usage::

    python main.py [options]

Options:
    -c / --config     Path to the station configuration JSON file.
                      Default: ``station_config.json``
    --once            Run one detection + requirements cycle and exit.
    --dry-run         Detect events and log actions without calling the API.
    --log-level       Override the log level from the config file.
                      Choices: DEBUG, INFO, WARNING, ERROR

Example::

    python main.py --config /etc/skyevents/station_config.json
    python main.py --once --dry-run
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from pathlib import Path
from types import FrameType

# ---------------------------------------------------------------------------
# Bootstrap: ensure the Reporter root is on sys.path so that local packages
# (config, auth, api, detectors, state, reporter) are importable regardless
# of where the script is launched from.
# ---------------------------------------------------------------------------

_REPORTER_ROOT = Path(__file__).resolve().parent
if str(_REPORTER_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPORTER_ROOT))

# These imports come after the path fix.
from api.client import SkyEventsApiClient  # noqa: E402
from auth.client import AuthClient, AuthError  # noqa: E402
from config.loader import load_config  # noqa: E402
from config.logging_setup import setup_logging  # noqa: E402
from reporter.scheduler import Scheduler  # noqa: E402
from state.tracker import StateTracker  # noqa: E402

logger = logging.getLogger("reporter.main")


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skyevents-reporter",
        description="SkyEvents station reporter — periodically scans for meteor "
        "detections and submits reports to the SkyEvents API.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="station_config.json",
        metavar="PATH",
        help="Path to station_config.json (default: station_config.json)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single detection + requirements cycle and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect events and log planned actions without calling the API.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        metavar="LEVEL",
        help="Override the log level defined in the config file.",
    )
    return parser


# ---------------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------------


def _install_signal_handlers(scheduler: Scheduler) -> None:
    """
    Register SIGINT and SIGTERM handlers for graceful shutdown.

    On Windows, only SIGINT (Ctrl-C) is reliably delivered.  SIGTERM is
    supported on Linux/macOS.

    @param scheduler  The running :class:`Scheduler` instance to stop.
    """

    def _handler(signum: int, _frame: FrameType | None) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Received %s — requesting graceful shutdown…", sig_name)
        scheduler.stop()

    signal.signal(signal.SIGINT, _handler)
    try:
        signal.signal(signal.SIGTERM, _handler)
    except (OSError, ValueError):
        # SIGTERM may not be available on all platforms (e.g. Windows threads).
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """
    Entry point.

    @return  Exit code: 0 on success, non-zero on error.
    """
    parser = _build_arg_parser()
    args = parser.parse_args()

    # --- Load and validate configuration -----------------------------------
    try:
        config = load_config(args.config)
    except FileNotFoundError as exc:
        # Logging is not yet set up; print to stderr.
        print(f"ERROR: Configuration file not found: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: Invalid configuration: {exc}", file=sys.stderr)
        return 1

    # --- Set up logging -----------------------------------------------------
    setup_logging(config.logging, override_level=args.log_level)
    logger.info("SkyEvents Reporter starting up…")
    logger.info("Config: %s", Path(args.config).resolve())

    if args.dry_run:
        logger.warning("DRY-RUN mode — no API calls will be made.")

    # --- Authenticate -------------------------------------------------------
    api_cfg = config.api
    auth = AuthClient(
        base_url=api_cfg.base_url,
        email=api_cfg.email,
        password=api_cfg.password,
        script_token=api_cfg.script_token or "",
        refresh_margin=api_cfg.token_refresh_margin_seconds,
        timeout=api_cfg.timeout_seconds,
    )

    try:
        auth.authenticate()
        logger.info("Authenticated successfully as '%s'.", api_cfg.email)
    except AuthError as exc:
        logger.critical("Authentication failed: %s", exc)
        return 1

    # --- Initialise components ---------------------------------------------
    state = StateTracker(config.state.db_path)
    api_client = SkyEventsApiClient(
        base_url=api_cfg.base_url,
        auth=auth,
        timeout=api_cfg.timeout_seconds,
    )
    scheduler = Scheduler(config, api_client, state, dry_run=args.dry_run)

    # --- Run ----------------------------------------------------------------
    exit_code = 0
    try:
        if args.once:
            logger.info("Running a single cycle (--once).")
            scheduler.run_once()
        else:
            _install_signal_handlers(scheduler)
            scheduler.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as exc:  # noqa: BLE001
        logger.critical("Fatal error: %s", exc, exc_info=True)
        exit_code = 2
    finally:
        api_client.close()
        state.close()
        logger.info("SkyEvents Reporter shut down.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
