"""
@file   Reporter/config/loader.py
@brief  Loads and validates the station configuration JSON file.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .models import StationReporterConfig


def load_config(path: str | Path) -> StationReporterConfig:
    """
    Load a ``station_config.json`` file and validate it against
    :class:`StationReporterConfig`.

    @param path  Path to the JSON configuration file.
    @return      Validated :class:`StationReporterConfig` instance.
    @raises FileNotFoundError  If the file does not exist.
    @raises ValueError         If the file contains invalid JSON or fails
                               Pydantic validation.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {p.resolve()}\n"
            "Copy station_config.example.json and fill in your settings."
        )

    try:
        with p.open("r", encoding="utf-8") as fh:
            raw: dict = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in config file '{p}': {exc}") from exc

    try:
        return StationReporterConfig.model_validate(raw)
    except ValidationError as exc:
        # Re-raise with a more user-friendly message.
        raise ValueError(
            f"Configuration validation failed in '{p}':\n{exc}"
        ) from exc
