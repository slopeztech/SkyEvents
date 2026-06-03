"""
@file   Reporter/config/logging_setup.py
@brief  Configures the Python logging system for the Reporter.

Sets up a rotating file handler and a console handler, both using
a structured timestamped format.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from .models import LoggingConfig


def setup_logging(cfg: LoggingConfig, override_level: str | None = None) -> None:
    """
    Apply the logging configuration from ``cfg``.

    @param cfg            Logging section of the station config.
    @param override_level If provided, overrides ``cfg.level`` (useful for
                          ``--verbose`` / ``--quiet`` CLI flags).
    """
    level_name = (override_level or cfg.level).upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # --- Console handler --------------------------------------------------
    console = logging.StreamHandler()
    console.setFormatter(fmt)

    # --- Rotating file handler --------------------------------------------
    log_path = Path(cfg.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    rotator = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=cfg.max_bytes,
        backupCount=cfg.backup_count,
        encoding="utf-8",
    )
    rotator.setFormatter(fmt)

    # Apply to the root logger; ``force=True`` replaces any handlers added
    # by earlier basicConfig calls (e.g. from imported libraries).
    logging.basicConfig(level=level, handlers=[console, rotator], force=True)

    # Quiet noisy third-party loggers.
    for noisy in ("urllib3", "requests", "charset_normalizer"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
