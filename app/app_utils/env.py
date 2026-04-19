"""Helpers for normalizing environment variable values."""

from __future__ import annotations

import os


def get_stripped_env(name: str, default: str | None = None) -> str | None:
    """Return an environment variable with surrounding whitespace removed.

    Empty or whitespace-only values are treated as unset and fall back to
    ``default``.
    """

    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip()
    if not normalized:
        return default

    return normalized
