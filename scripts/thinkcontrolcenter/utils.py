"""Shared utility functions for file I/O, logging setup, and privileged execution."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def read_file(path: str, default: str = "") -> str:
    """Safely read the full text content of a file.

    Args:
        path: Absolute path to the file.
        default: Value to return if the file cannot be read.

    Returns:
        The file content as a string, or *default* on any I/O error.
    """
    try:
        with open(path, "r") as f:
            return f.read()
    except OSError as exc:
        logger.debug("Could not read %s: %s", path, exc)
        return default


def read_file_stripped(path: str, default: str = "") -> str:
    """Read a file and return its stripped content."""
    return read_file(path, default).strip()


def get_style_css_path() -> str:
    """Return the absolute path to the bundled ``style.css`` file."""
    return os.path.join(os.path.dirname(__file__), "style.css")
