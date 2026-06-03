"""
@file   Reporter/state/tracker.py
@brief  SQLite-backed state tracker for processed files and uploads.

The :class:`StateTracker` maintains a local SQLite database that records
which detection files have been processed (report created) and which files
have been uploaded as attachments for pending requirements.  It also stores
the timestamp of the last successful scan per device so that detectors can
be called with an appropriate *since* parameter.

Database schema:

    processed_files(
        file_path    TEXT PRIMARY KEY,   -- absolute normalised path
        file_hash    TEXT,               -- SHA-256 of file contents (optional)
        processed_at TEXT,               -- ISO-8601 UTC
        report_id    TEXT                -- SkyEvents report UUID
    )

    uploaded_attachments(
        file_path       TEXT,            -- absolute normalised path
        requirement_id  TEXT,            -- SkyEvents requirement UUID
        uploaded_at     TEXT,            -- ISO-8601 UTC
        PRIMARY KEY (file_path, requirement_id)
    )

    scan_times(
        device_hash_id  TEXT PRIMARY KEY,
        last_scan_at    TEXT             -- ISO-8601 UTC
    )
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_files (
    file_path    TEXT PRIMARY KEY,
    file_hash    TEXT,
    processed_at TEXT NOT NULL,
    report_id    TEXT
);

CREATE TABLE IF NOT EXISTS uploaded_attachments (
    file_path      TEXT NOT NULL,
    requirement_id TEXT NOT NULL,
    uploaded_at    TEXT NOT NULL,
    PRIMARY KEY (file_path, requirement_id)
);

CREATE TABLE IF NOT EXISTS scan_times (
    device_hash_id TEXT PRIMARY KEY,
    last_scan_at   TEXT NOT NULL
);
"""


class StateTracker:
    """
    Persistent state store backed by a local SQLite database.

    The database is created automatically if it does not exist.  All
    file paths are normalised via :func:`pathlib.Path.resolve` before
    storage so that relative/absolute variants of the same path compare
    equal.

    @param db_path  Path to the SQLite database file.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.debug("StateTracker opened: %s", self._db_path)

    # ------------------------------------------------------------------
    # Processed files
    # ------------------------------------------------------------------

    def is_file_processed(self, path: str) -> bool:
        """
        Check whether *path* has already been processed (report created).

        @param path  Absolute path to the detection file.
        @return      ``True`` if the file is in the processed-files table.
        """
        norm = self._norm(path)
        row = self._conn.execute(
            "SELECT 1 FROM processed_files WHERE file_path = ?", (norm,)
        ).fetchone()
        return row is not None

    def mark_file_processed(
        self, path: str, report_id: str, file_hash: str = ""
    ) -> None:
        """
        Record that *path* has been processed and a report created.

        @param path       Absolute path to the detection file.
        @param report_id  UUID of the created report.
        @param file_hash  Optional SHA-256 hash of the file contents.
        """
        norm = self._norm(path)
        now = _utcnow_iso()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO processed_files
                (file_path, file_hash, processed_at, report_id)
            VALUES (?, ?, ?, ?)
            """,
            (norm, file_hash, now, report_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Uploaded attachments
    # ------------------------------------------------------------------

    def is_uploaded(self, path: str, requirement_id: str) -> bool:
        """
        Check whether *path* has already been uploaded for *requirement_id*.

        @param path            Absolute path to the file.
        @param requirement_id  UUID of the SkyEvents requirement.
        @return                ``True`` if the upload is already recorded.
        """
        norm = self._norm(path)
        row = self._conn.execute(
            "SELECT 1 FROM uploaded_attachments WHERE file_path = ? AND requirement_id = ?",
            (norm, requirement_id),
        ).fetchone()
        return row is not None

    def mark_uploaded(self, path: str, requirement_id: str) -> None:
        """
        Record that *path* has been successfully uploaded for *requirement_id*.

        @param path            Absolute path to the file.
        @param requirement_id  UUID of the SkyEvents requirement.
        """
        norm = self._norm(path)
        now = _utcnow_iso()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO uploaded_attachments
                (file_path, requirement_id, uploaded_at)
            VALUES (?, ?, ?)
            """,
            (norm, requirement_id, now),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Scan timestamps
    # ------------------------------------------------------------------

    def get_last_scan_time(self, device_hash_id: str) -> datetime | None:
        """
        Return the UTC timestamp of the last successful scan for a device.

        @param device_hash_id  Device hash ID from the station config.
        @return                UTC-aware :class:`datetime`, or ``None`` if
                               the device has never been scanned.
        """
        row = self._conn.execute(
            "SELECT last_scan_at FROM scan_times WHERE device_hash_id = ?",
            (device_hash_id,),
        ).fetchone()
        if row is None:
            return None
        try:
            return datetime.fromisoformat(row[0]).replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def set_last_scan_time(self, device_hash_id: str, dt: datetime) -> None:
        """
        Persist the scan timestamp for a device.

        @param device_hash_id  Device hash ID from the station config.
        @param dt              The UTC timestamp to store.
        """
        self._conn.execute(
            """
            INSERT OR REPLACE INTO scan_times (device_hash_id, last_scan_at)
            VALUES (?, ?)
            """,
            (device_hash_id, dt.isoformat()),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> "StateTracker":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _norm(path: str) -> str:
        """Normalise a path to a consistent absolute string."""
        return str(Path(path).resolve())


def _utcnow_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
