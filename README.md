# SkyEvents

A Django-based platform for coordinating a network of meteor observation stations. Each station runs a local script that records detections, manages data files, and synchronises with the central server via a REST API.

## Table of Contents

- [SkyEvents](#skyevents)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Tech Stack](#tech-stack)
  - [Project Structure](#project-structure)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Local development (Docker)](#local-development-docker)
    - [Local development (bare metal)](#local-development-bare-metal)
  - [Environment Variables](#environment-variables)
  - [Running Tests](#running-tests)
  - [REST API v1](#rest-api-v1)
    - [Authentication](#authentication)
      - [Layer 1 — JWT (JSON Web Token)](#layer-1--jwt-json-web-token)
      - [Layer 2 — Script Token](#layer-2--script-token)
      - [Full request example](#full-request-example)
      - [Throttling](#throttling)
    - [Endpoints](#endpoints)
      - [Auth](#auth)
      - [Station script](#station-script)
        - [`POST /api/v1/station/reports/`](#post-apiv1stationreports)
        - [`GET /api/v1/station/requirements/`](#get-apiv1stationrequirements)
        - [`POST /api/v1/station/requirements/{id}/media/`](#post-apiv1stationrequirementsidmedia)
    - [Station script workflow](#station-script-workflow)
  - [User Roles](#user-roles)
  - [Models at a Glance](#models-at-a-glance)

---

## Overview

SkyEvents lets a network admin manage a fleet of observation stations, each equipped with one or more cameras and/or radio receivers. When a station detects an astronomical event (meteor, fireball, …) it:

1. Creates a detection **report** in the database via the API.
2. Checks for any pending **media requirements** — file-upload requests queued by the admin.
3. **Uploads** the requested local files back to the server.

The web dashboard (Django + Tailwind CSS) allows admins to review reports, link them to confirmed astronomical events, manage devices, and create media requirements.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Django 5.1 |
| REST API | Django REST Framework 3.15 + drf-spectacular (OpenAPI 3.1) |
| Authentication | `djangorestframework-simplejwt` 5.4 |
| Database | PostgreSQL 16 (psycopg v3) |
| Cache / broker | Redis 7 |
| Async tasks | Celery 5 + django-celery-beat |
| Frontend | Tailwind CSS 3 (compiled via `tailwindcss` CLI) |
| Logging | structlog + django-structlog |
| Security | django-axes (brute-force), django-csp, django-cors-headers |
| Testing | pytest-django + factory_boy |
| Primary keys | UUIDv7 (time-sortable, `uuid6` library) |

---

## Project Structure

```
SkyEvents/
├── config/
│   ├── settings/
│   │   ├── base.py          # Shared settings
│   │   ├── local.py         # Development overrides
│   │   ├── test.py          # Test overrides
│   │   └── production.py    # Production overrides
│   ├── urls.py              # Root URL configuration
│   └── celery.py            # Celery application
│
├── sky_events/
│   └── apps/
│       ├── core/            # Abstract models, exceptions, pagination
│       │   └── api/         # Shared API permissions, throttles, URL router
│       ├── users/           # Custom User model + JWT endpoints
│       ├── station/         # Observation station model
│       ├── camera/          # Camera model (fixed / all-sky / wide-angle)
│       ├── radio/           # Radio receiver model
│       ├── events/          # Astronomical events
│       ├── reports/         # Detection reports, files & media requirements
│       │   └── api/         # Station-script REST API views
│       ├── notices/         # Public event notices
│       └── webconfig/       # Site-wide configuration
│
├── tests/                   # pytest test suite
│   ├── factories.py         # factory_boy factories
│   ├── test_api/            # API integration tests
│   ├── test_cameras/
│   ├── test_stations/
│   └── test_users/
│
├── theme/                   # Tailwind CSS source
├── locale/                  # i18n translation files (en / es)
├── docker-compose.yml
└── Dockerfile
```

---

## Getting Started

### Prerequisites

- Docker + Docker Compose **or** Python 3.12 + PostgreSQL 16 + Redis 7
- Node.js 18+ (only needed to rebuild Tailwind CSS)

### Local development (Docker)

```bash
# Start all services (db, redis, web, worker, beat)
docker compose up -d

# Apply migrations
docker compose exec web python manage.py migrate

# Create a superuser
docker compose exec web python manage.py createsuperuser

# Tail logs
docker compose logs -f web
```

The app will be available at **http://localhost:8000**.

### Local development (bare metal)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements/dev.txt

# 3. Copy the environment file and fill in the values
cp .env.example .env

# 4. Apply migrations
python manage.py migrate

# 5. Build Tailwind CSS (first time or after template changes)
cd theme/static_src && npm install && npm run build && cd ../..

# 6. Run the development server
python manage.py runserver
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | ✅ | Django secret key |
| `DJANGO_DEBUG` | — | `True` in development (default: `False`) |
| `DJANGO_ALLOWED_HOSTS` | ✅ | Comma-separated list of allowed hosts |
| `DATABASE_URL` | ✅ | PostgreSQL DSN (`postgres://user:pass@host/db`) |
| `REDIS_URL` | ✅ | Redis URL (`redis://host:6379/0`) |
| `ADMIN_URL` | — | Custom admin path (default: `admin/`) |
| `DJANGO_MEDIA_ROOT` | — | Filesystem path for uploaded media |

---

## Running Tests

```bash
# Full test suite
python -m pytest

# Only API tests
python -m pytest tests/test_api/ -v

# With coverage
python -m pytest --cov=sky_events --cov-report=term-missing
```

---

## REST API v1

Base URL: `/api/v1/`

Interactive docs (Swagger UI): `/api/docs/`  
ReDoc: `/api/redoc/`  
OpenAPI schema (JSON): `/api/schema/`

### Authentication

The API uses **two layers of authentication** specifically designed for autonomous station scripts:

#### Layer 1 — JWT (JSON Web Token)

Obtain a token pair by posting the user's credentials:

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "station_owner",
  "password": "secret"
}
```

Response:

```json
{
  "access": "<access_token>",
  "refresh": "<refresh_token>"
}
```

Refresh an expired access token:

```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{ "refresh": "<refresh_token>" }
```

#### Layer 2 — Script Token

Every station API endpoint additionally requires the `X-Script-Token` header. The value must match the `script_token` field on the authenticated user's profile (visible in the dashboard).

This two-factor design means a stolen JWT alone is not enough to access station endpoints.

#### Full request example

```http
POST /api/v1/station/reports/
Authorization: Bearer <access_token>
X-Script-Token: <script_token>
Content-Type: application/json
```

#### Throttling

Station endpoints are rate-limited to **10 000 requests per hour** per authenticated user.

---

### Endpoints

#### Auth

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/token/` | Obtain JWT access + refresh tokens |
| `POST` | `/api/v1/auth/token/refresh/` | Refresh an access token |
| `POST` | `/api/v1/auth/token/verify/` | Verify a token is still valid |
| `GET` | `/api/v1/auth/me/` | Return the current user's profile |

#### Station script

All endpoints below require `Authorization: Bearer <token>` **and** `X-Script-Token: <script_token>`.

---

##### `POST /api/v1/station/reports/`

Create a detection report. The station is identified by `station_hash_id` (the opaque token shown in the station's configuration page). Optional camera/radio identifiers are resolved against the same station; unknown IDs are silently ignored so the report is still accepted.

**Request body** (`application/json`)

```json
{
  "station_hash_id": "a1b2c3d4e5f6a1b2c3d4e5f6",
  "camera_hash_id": "112233445566112233445566",
  "radio_hash_id": "",
  "recorded_at": "2024-08-15T22:30:00Z",
  "duration_ms": 1500,
  "notes": "Bright fireball, magnitude estimated -4",
  "files": [
    {
      "file_type": "video",
      "filename": "/data/detections/2024-08-15/event_001.mp4",
      "file_size_bytes": 104857600,
      "description": "Full-resolution capture"
    },
    {
      "file_type": "spectrogram",
      "filename": "/data/detections/2024-08-15/event_001_spec.png"
    }
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `station_hash_id` | string | ✅ | Station's opaque hash identifier |
| `camera_hash_id` | string | — | Camera's hash ID (must belong to the station) |
| `radio_hash_id` | string | — | Radio receiver's hash ID (must belong to the station) |
| `recorded_at` | ISO 8601 datetime | ✅ | UTC timestamp of detection onset |
| `duration_ms` | integer | — | Detection duration in milliseconds |
| `notes` | string | — | Free-text operator notes |
| `files` | array | — | List of local file metadata records |

`file_type` choices: `video`, `image`, `spectrogram`, `audio`, `data`, `other`

**Response `201 Created`**

```json
{ "id": "01930000-0000-7000-0000-000000000000", "status": "pending" }
```

---

##### `GET /api/v1/station/requirements/`

Return all *pending* media requirements for the authenticated user's stations. Requirements with a past `expires_at` are excluded automatically.

**Response `200 OK`**

```json
[
  {
    "id": "01930000-0000-7000-0000-000000000001",
    "station_code": "stn-0001",
    "requested_paths": [
      "/data/2024-08-15/event_001.mp4",
      "/data/2024-08-15/event_001_spec.png"
    ],
    "status": "pending",
    "notes": "Needed for event EVT-2024-08-15-001 analysis",
    "expires_at": "2024-08-22T00:00:00Z",
    "created_at": "2024-08-15T23:00:00Z"
  }
]
```

---

##### `POST /api/v1/station/requirements/{id}/media/`

Upload a file to fulfil a media requirement. Accepts `multipart/form-data`. Maximum file size is **500 MB**.

After each successful upload the server checks whether all `requested_paths` have been covered. If so, the requirement is automatically marked as `fulfilled`.

**Request** (`multipart/form-data`)

| Field | Required | Description |
|---|---|---|
| `file` | ✅ | The file to upload |
| `original_path` | ✅ | The local path on the station (must match one of `requested_paths`) |
| `file_type` | ✅ | One of: `video`, `image`, `spectrogram`, `audio`, `data`, `other` |

**Response `201 Created`**

```json
{
  "id": "01930000-0000-7000-0000-000000000002",
  "requirement_status": "fulfilled"
}
```

`requirement_status` is `"pending"` until all requested paths have been uploaded, then switches to `"fulfilled"`.

---

### Station script workflow

A minimal Python script for a station would follow this sequence:

```python
import requests

BASE = "https://skyevents.example.com/api/v1"
HEADERS = {}

# 1. Authenticate
r = requests.post(f"{BASE}/auth/token/", json={"username": "owner1", "password": "..."})
access = r.json()["access"]
HEADERS = {
    "Authorization": f"Bearer {access}",
    "X-Script-Token": "<script_token_from_profile>",
}

# 2. Create a detection report
r = requests.post(f"{BASE}/station/reports/", json={
    "station_hash_id": "<hash_id>",
    "recorded_at": "2024-08-15T22:30:00Z",
    "files": [
        {"file_type": "video", "filename": "/data/event.mp4", "file_size_bytes": 104857600}
    ],
}, headers=HEADERS)
print("Report created:", r.json()["id"])

# 3. Check for pending requirements
requirements = requests.get(f"{BASE}/station/requirements/", headers=HEADERS).json()

# 4. Upload each requested file
for req in requirements:
    for path in req["requested_paths"]:
        with open(path, "rb") as f:
            requests.post(
                f"{BASE}/station/requirements/{req['id']}/media/",
                data={"original_path": path, "file_type": "video"},
                files={"file": f},
                headers=HEADERS,
            )
```

---

## User Roles

| Role | Description |
|---|---|
| `ADMIN` | Full access to the web dashboard and all API resources |
| `STATION_OWNER` | Can manage their own stations, cameras, radios and reports; uses the station-script API |

---

## Models at a Glance

```
User
 └── Station (owner FK)
      ├── Camera (station FK)
      ├── RadioReceiver (station FK)
      ├── StationReport (station FK)
      │    └── ReportFile  ← local file metadata (no upload)
      └── MediaRequirement (station FK)
           └── ReportAttachment  ← actual uploaded file
```

| Model | Purpose |
|---|---|
| `Station` | Physical observation site with GPS coordinates and timezone |
| `Camera` | Camera device; type: `fixed` / `allsky` / `wide`; azimuth + elevation |
| `RadioReceiver` | SDR-based radio receiver with frequency and bandwidth |
| `StationReport` | Detection record produced by a station; linked (optionally) to an `AstronomicalEvent` |
| `ReportFile` | Metadata for a file on the station's local storage (path, size, type) |
| `AstronomicalEvent` | Admin-confirmed event that aggregates multiple reports |
| `MediaRequirement` | Admin request for specific local files from a station |
| `ReportAttachment` | Uploaded file that fulfils a `MediaRequirement` |
