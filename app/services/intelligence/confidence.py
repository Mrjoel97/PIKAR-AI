"""Generic weighted confidence scorer and band classifier.

Used by per-agent presets (presets/research.py, presets/data.py, ...).
"""

from __future__ import annotations

from collections.abc import Mapping

from app.services.intelligence.schemas import ConfidenceBand


def score_confidence(
    inputs: Mapping[str, float],
    weights: Mapping[str, float],
) -> float:
    """Stub — implemented in Task 4. Do not call yet."""
    raise NotImplementedError("Implemented in Plan 112-02 Task 4")


def to_band(
    score: float,
    *,
    low_threshold: float = 0.50,
    high_threshold: float = 0.75,
) -> ConfidenceBand:
    """Stub — implemented in Task 4. Do not call yet."""
    raise NotImplementedError("Implemented in Plan 112-02 Task 4")
