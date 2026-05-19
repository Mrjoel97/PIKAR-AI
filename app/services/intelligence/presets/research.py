"""Research-domain confidence preset.

Bit-identical replacement for app/agents/research/tools/synthesizer.py:
calculate_confidence. Will be wired up in Plan 112-05 (Research refactor).
"""

from __future__ import annotations


def research_confidence(
    track_agreement: float,
    source_quality: float,
    freshness: float,
    contradictions_found: int,
) -> float:
    """Stub — implemented in Task 4. Do not call yet."""
    raise NotImplementedError("Implemented in Plan 112-02 Task 4")
