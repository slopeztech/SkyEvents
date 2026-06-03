"""
@file   Reporter/detectors/registry.py
@brief  Factory and registry for all detector implementations.

Add a new detector class by importing it here and adding a lowercase
alias to :data:`_REGISTRY`.  The scheduler and CLI reference detectors
only by their string name (taken from ``DeviceConfig.detector``), so no
other file needs changing.

Usage::

    from detectors.registry import create_detector

    detector = create_detector("ufocapture", "/data/captures", {"date_subfolders": True})
    events = detector.scan(since=last_scan)
"""

from __future__ import annotations

from typing import Any

from .allskeye import AllSkyEyeDetector
from .base import BaseDetector
from .echoes import EchoesDetector
from .generic import GenericDetector
from .meteordl import MeteorDLDetector
from .metrec import MetRecDetector
from .rms import RMSDetector
from .ufocapture import UFOCaptureDetector

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

#: Maps lowercase detector name strings to their implementing class.
_REGISTRY: dict[str, type[BaseDetector]] = {
    "generic": GenericDetector,
    "ufocapture": UFOCaptureDetector,
    "rms": RMSDetector,
    "allskeye": AllSkyEyeDetector,
    "meteordl": MeteorDLDetector,
    "metrec": MetRecDetector,
    "echoes": EchoesDetector,
}


def create_detector(
    name: str,
    watch_path: str,
    options: dict[str, Any] | None = None,
) -> BaseDetector:
    """
    Instantiate a detector by its registered name.

    @param name        Case-insensitive detector name (e.g. ``"ufocapture"``).
    @param watch_path  Path to the directory the detector should scan.
    @param options     Optional dict of detector-specific options.
    @return            A configured :class:`BaseDetector` subclass instance.
    @raises ValueError If *name* is not registered.
    """
    key = name.lower()
    cls = _REGISTRY.get(key)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(
            f"Unknown detector '{name}'. Available detectors: {available}"
        )
    return cls(watch_path, options)


def list_detectors() -> list[str]:
    """
    Return a sorted list of all registered detector names.

    @return  Sorted list of lowercase detector name strings.
    """
    return sorted(_REGISTRY)
