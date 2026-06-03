# SkyEvents Reporter

A standalone Python station script that periodically scans meteor-capture software output directories, submits detection reports to the SkyEvents API, and uploads files requested by the server.

Works on **Windows** and **Linux**. Requires Python 3.10+.

---

## Features

- Supports multiple capture-software formats out of the box
- JWT + `X-Script-Token` dual authentication with automatic token refresh
- SQLite state database — never submits or uploads the same file twice
- Configurable polling intervals and per-cycle file caps
- `--once` mode for cron / task-scheduler integration
- `--dry-run` mode for safe testing without hitting the API
- Graceful shutdown on SIGINT / SIGTERM

---

## Supported Detectors

| Name | Software | Platform |
|---|---|---|
| `ufocapture` | UFOCapture / UFOCaptureHD2 (SonotaCo) | Windows |
| `rms` | RMS — Raspberry Meteor Station | Linux / RPi |
| `allskeye` | AllSkyEye | Windows / Linux |
| `meteordl` | MeteorDL / CAMS | Windows / Linux |
| `metrec` | MetRec (Sirko Molau) | Windows / Linux |
| `echoes` | Echoes (radio forward-scatter) | Windows / Linux |
| `generic` | Any folder + glob pattern | Windows / Linux |

---

## Installation

```bash
# Create a virtual environment (recommended)
python -m venv .venv

# Activate it
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Copy the example config and edit it with your station details:

```bash
cp station_config.example.json station_config.json
```

### Configuration file structure

```jsonc
{
  "api": {
    "base_url": "https://skyevents.example.com/api/v1",
    "username": "my_station_user",
    "password": "my_secure_password",
    "script_token": "",           // auto-fetched from /auth/me/ if empty
    "token_refresh_margin_seconds": 300,
    "timeout_seconds": 60
  },

  "station": {
    "hash_id": "ABCDE12345"       // provided by the SkyEvents administrator
  },

  "devices": {
    "cameras": [
      {
        "hash_id": "CAM001",      // camera hash_id from SkyEvents
        "name": "Main Camera",
        "detector": "ufocapture",
        "watch_path": "C:\\UFOCapture\\captures",
        "detector_options": {
          "date_subfolders": false
        }
      }
    ],
    "radios": [
      {
        "hash_id": "RAD001",
        "name": "Echoes Radio",
        "detector": "echoes",
        "watch_path": "C:\\Echoes\\data",
        "detector_options": {}
      }
    ]
  },

  "scheduler": {
    "poll_interval_seconds": 300,           // detection cycle interval
    "max_files_per_cycle": 50,              // cap to avoid flooding on first run
    "requirements_poll_interval_seconds": 600
  },

  "state": {
    "db_path": "./reporter_state.db"        // SQLite state file path
  },

  "logging": {
    "level": "INFO",
    "file": "./reporter.log",
    "max_bytes": 10485760,
    "backup_count": 5
  }
}
```

The administrator will provide the `station.hash_id` and each device's `hash_id` through the SkyEvents web panel.

---

## Usage

### Continuous mode (recommended for production)

```bash
python main.py
python main.py --config /etc/skyevents/station_config.json
```

### Single cycle (cron / Task Scheduler)

```bash
python main.py --once
```

### Dry run (no API calls)

```bash
python main.py --dry-run
python main.py --once --dry-run
```

### Override log level

```bash
python main.py --log-level DEBUG
```

### Full options

```
python main.py --help

usage: skyevents-reporter [-h] [-c PATH] [--once] [--dry-run] [--log-level LEVEL]

options:
  -c PATH, --config PATH   Path to station_config.json (default: station_config.json)
  --once                   Run a single detection + requirements cycle and exit
  --dry-run                Log planned actions without calling the API
  --log-level LEVEL        Override log level: DEBUG, INFO, WARNING, ERROR
```

---

## Detector Options Reference

### `ufocapture`

| Option | Type | Default | Description |
|---|---|---|---|
| `date_subfolders` | bool | `false` | Scan one level of `YYYYMMDD/` subdirectories |
| `extensions` | list | `[".avi",".jpg",".xml",".bmp"]` | File extensions to collect |

### `rms`

| Option | Type | Default | Description |
|---|---|---|---|
| `station_code` | string | `""` | Filter directories by station prefix |
| `subdir` | string | `"ArchivedFiles"` | Subdirectory inside watch_path to scan |

### `allskeye`

| Option | Type | Default | Description |
|---|---|---|---|
| `csv_pattern` | string | `"Events_*.csv"` | Glob for detection CSV files |
| `video_subdir` | string | `"Videos"` | Subdirectory containing video files |
| `delimiter` | string | `","` | CSV field delimiter |

### `meteordl`

No specific options required. Any event directory containing a `YYYYMMDD_HHMMSS` timestamp in its name is recognised automatically.

### `metrec`

| Option | Type | Default | Description |
|---|---|---|---|
| `file_pattern` | string | `"*.met"` | Glob for MetRec data files |

### `echoes`

| Option | Type | Default | Description |
|---|---|---|---|
| `csv_pattern` | string | `"echoes_*.csv"` | Glob for observation CSV files |
| `spec_subdir` | string | `""` | Subdirectory for spectrogram images |
| `delimiter` | string | `","` | CSV field delimiter |

### `generic`

| Option | Type | Default | Description |
|---|---|---|---|
| `pattern` | string | `"*.mp4"` | Glob pattern to match |
| `recursive` | bool | `false` | Recurse into subdirectories |
| `file_type` | string | `""` | Force a specific file_type (auto-detected if empty) |

---

## Project Structure

```
Reporter/
├── main.py                        # Entry point
├── requirements.txt
├── station_config.example.json    # Example configuration
├── utils.py                       # File-type inference helpers
├── config/
│   ├── models.py                  # Pydantic configuration models
│   ├── loader.py                  # JSON → validated config
│   └── logging_setup.py           # Rotating file + console logging
├── auth/
│   └── client.py                  # JWT auth, auto-refresh, X-Script-Token
├── api/
│   └── client.py                  # HTTP client for SkyEvents API v1
├── detectors/
│   ├── base.py                    # DetectionFile, DetectionEvent, BaseDetector
│   ├── generic.py
│   ├── ufocapture.py
│   ├── rms.py
│   ├── allskeye.py
│   ├── meteordl.py
│   ├── metrec.py
│   ├── echoes.py
│   └── registry.py                # create_detector() factory
├── state/
│   └── tracker.py                 # SQLite state (processed files, uploads, scan times)
└── reporter/
    ├── builder.py                 # DetectionEvent → API payload
    ├── scanner.py                 # Per-device detection cycle
    ├── uploader.py                # Requirements / attachment uploader
    └── scheduler.py               # Periodic loop with graceful shutdown
```

---

## Running as a Service

### Windows — Task Scheduler

Create a basic task with:
- **Program:** `C:\path\to\python.exe`
- **Arguments:** `C:\path\to\Reporter\main.py --config C:\path\to\station_config.json`
- **Trigger:** At startup, repeat every 5 minutes

Or use the `--once` flag with a scheduled trigger and let the scheduler handle the interval externally.

### Linux — systemd

```ini
# /etc/systemd/system/skyevents-reporter.service
[Unit]
Description=SkyEvents Reporter
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/skyevents/Reporter
ExecStart=/opt/skyevents/Reporter/.venv/bin/python main.py --config /etc/skyevents/station_config.json
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now skyevents-reporter
sudo journalctl -u skyevents-reporter -f
```

---

## Adding a New Detector

1. Create `detectors/mysoftware.py` and subclass `BaseDetector`:

```python
from .base import BaseDetector, DetectionEvent

class MySoftwareDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "MySoftware"

    def scan(self, since=None) -> list[DetectionEvent]:
        ...
```

2. Register it in `detectors/registry.py`:

```python
from .mysoftware import MySoftwareDetector

_REGISTRY: dict[str, type[BaseDetector]] = {
    ...
    "mysoftware": MySoftwareDetector,
}
```

3. Use `"detector": "mysoftware"` in `station_config.json`.

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `requests` | ≥ 2.31 | HTTP client |
| `pydantic` | ≥ 2.7 | Configuration validation |

No other third-party dependencies. All other modules used (`sqlite3`, `pathlib`, `threading`, `logging`, `csv`, `re`, …) are part of the Python standard library.
