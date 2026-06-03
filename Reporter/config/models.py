"""
@file   Reporter/config/models.py
@brief  Pydantic v2 configuration models for the SkyEvents Reporter.

The entire station configuration is loaded from a single JSON file
(``station_config.json``) and validated against these models at startup.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ApiConfig(BaseModel):
    """
    Connection and authentication settings for the SkyEvents API.

    @var base_url                      Full URL including the ``/api/v1`` prefix.
    @var email                         Login e-mail for the station owner account.
    @var password                      Login password.
    @var script_token                  Optional.  If left empty the reporter will
                                       fetch it from ``/api/v1/auth/me/`` after the
                                       first successful authentication.
    @var token_refresh_margin_seconds  Refresh the JWT access token this many
                                       seconds before it actually expires.
    @var timeout_seconds               HTTP request timeout.
    """

    base_url: str
    email: str
    password: str
    script_token: str = ""
    token_refresh_margin_seconds: int = 300
    timeout_seconds: int = 60

    @field_validator("base_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")


class StationConfig(BaseModel):
    """
    Station identification.

    @var hash_id  The opaque station identifier shown in the SkyEvents dashboard.
    """

    hash_id: str


class DeviceConfig(BaseModel):
    """
    Configuration for a single observation device (camera or radio receiver).

    @var hash_id            Device hash identifier from the SkyEvents dashboard.
    @var name               Human-readable label (for log messages only).
    @var detector           Name of the detection software adapter.  Must be one of
                            the values registered in ``detectors/registry.py``
                            (e.g. ``generic``, ``ufocapture``, ``rms``, …).
    @var watch_path         Filesystem path that the detector will scan for new files.
    @var detector_options   Free-form dict passed verbatim to the detector constructor.
                            Valid keys depend on the chosen detector.
    """

    hash_id: str
    name: str
    detector: str
    watch_path: str
    detector_options: dict[str, Any] = Field(default_factory=dict)


class DevicesConfig(BaseModel):
    """
    Lists of cameras and radio receivers attached to the station.

    @var cameras  Optical camera devices.
    @var radios   Radio receiver devices.
    """

    cameras: list[DeviceConfig] = Field(default_factory=list)
    radios: list[DeviceConfig] = Field(default_factory=list)

    @property
    def all_devices(self) -> list[tuple[str, DeviceConfig]]:
        """Return all devices tagged with their type (``"camera"`` or ``"radio"``)."""
        return [(("camera"), d) for d in self.cameras] + [
            ("radio", d) for d in self.radios
        ]


class SchedulerConfig(BaseModel):
    """
    Periodic-task timing configuration.

    @var poll_interval_seconds              Seconds between detection scans.
    @var max_files_per_cycle                Maximum files processed per device per cycle
                                            (prevents overwhelming the API on first run).
    @var requirements_poll_interval_seconds Seconds between requirement checks.
    @var ping_interval_seconds              Seconds between heartbeat pings to the API.
    """

    poll_interval_seconds: int = 300
    max_files_per_cycle: int = 50
    requirements_poll_interval_seconds: int = 600
    ping_interval_seconds: int = 20


class StateConfig(BaseModel):
    """
    Persistent-state storage settings.

    @var db_path  Path to the SQLite database file used to track processed files.
    """

    db_path: str = "./reporter_state.db"


class LoggingConfig(BaseModel):
    """
    Logging configuration.

    @var level        Python logging level name (``DEBUG``, ``INFO``, ``WARNING``, …).
    @var file         Path to the rotating log file.
    @var max_bytes    Maximum size of a single log file before rotation.
    @var backup_count Number of rotated log files to keep.
    """

    level: str = "INFO"
    file: str = "./reporter.log"
    max_bytes: int = 10_485_760  # 10 MB
    backup_count: int = 5


class StationReporterConfig(BaseModel):
    """
    Root configuration model.  Validated against ``station_config.json`` at startup.
    """

    api: ApiConfig
    station: StationConfig
    devices: DevicesConfig
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    state: StateConfig = Field(default_factory=StateConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
