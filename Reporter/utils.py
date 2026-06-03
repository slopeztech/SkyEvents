"""
@file   Reporter/utils.py
@brief  Shared utility functions for the SkyEvents Reporter.

Provides file-type inference and human-readable formatting helpers
used across all Reporter modules.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# File-type mapping
# ---------------------------------------------------------------------------

#: Maps lowercase file extensions to SkyEvents API ``file_type`` values.
_EXT_TO_FILE_TYPE: dict[str, str] = {
    # Video
    ".mp4": "video",
    ".avi": "video",
    ".mkv": "video",
    ".mov": "video",
    ".wmv": "video",
    ".ts":  "video",
    ".m4v": "video",
    # Images / astronomy formats
    ".jpg":  "image",
    ".jpeg": "image",
    ".png":  "image",
    ".tiff": "image",
    ".tif":  "image",
    ".fits": "image",
    ".fit":  "image",
    ".bmp":  "image",
    # Audio
    ".wav":  "audio",
    ".mp3":  "audio",
    ".flac": "audio",
    ".ogg":  "audio",
    # Data / metadata
    ".csv":         "data",
    ".txt":         "data",
    ".json":        "data",
    ".xml":         "data",
    ".dat":         "data",
    ".met":         "data",
    ".ftpdetect":   "data",
}

#: Keywords in the file stem (lowercase) that indicate a spectrogram image.
_SPECTROGRAM_KEYWORDS: tuple[str, ...] = (
    "spec",
    "spectrogram",
    "fft",
    "spectrum",
)


def guess_file_type(path: Path | str) -> str:
    """
    Infer the SkyEvents ``file_type`` value from a file path.

    Spectrograms are detected by looking for keywords in the file stem
    before falling back to the extension table.

    @param path  Path to the file (only the name and extension are used).
    @return      One of ``video``, ``image``, ``spectrogram``,
                 ``audio``, ``data``, or ``other``.
    """
    p = Path(path)
    ext = p.suffix.lower()
    stem = p.stem.lower()

    # PNG/JPEG files whose names contain spectrogram-related words.
    if ext in (".png", ".jpg", ".jpeg") and any(
        kw in stem for kw in _SPECTROGRAM_KEYWORDS
    ):
        return "spectrogram"

    return _EXT_TO_FILE_TYPE.get(ext, "other")


def format_bytes(size: int) -> str:
    """
    Return a human-readable string for *size* bytes.

    @param size  Number of bytes.
    @return      Formatted string such as ``"12.5 MB"``.
    """
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0  # type: ignore[assignment]
    return f"{size:.1f} PB"
