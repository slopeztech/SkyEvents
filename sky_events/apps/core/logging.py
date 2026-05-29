"""
Structured logging configuration for SkyEvents.

Configures structlog to produce consistent JSON log output in production
and readable coloured output in development.

@file   sky_events/apps/core/logging.py
@author slopez.tech
"""

from __future__ import annotations

import logging

import structlog


def configure_structlog() -> None:
    """
    Configure structlog processors and output format.

    This function is called once during Django startup (in CoreConfig.ready).
    It should NOT be called again after initialisation.
    """
    shared_processors: list[structlog.types.Processor] = [
        # Merge context variables (e.g., request_id, user_id)
        structlog.contextvars.merge_contextvars,
        # Add log level as a string
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Format positional arguments as %s-style strings
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Add ISO 8601 timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Render stack info (tracebacks)
        structlog.processors.StackInfoRenderer(),
        # Format exceptions
        structlog.processors.ExceptionRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            # Wrap for stdlib ProcessorFormatter (renders to JSON via LOGGING config)
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
