"""Shared intelligence infrastructure used by agents.

This package exposes:
- score_confidence / to_band — generic weighted scorer and band classifier
- presets — named confidence formulas per agent domain
- ConfidenceBand — Literal["low", "medium", "high"]

Plan 112-03 will add claims (kg_findings writer/reader) to this surface.
Plan 112-04 will add adaptive cache. See the design at
docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md.
"""

from app.services.intelligence import presets
from app.services.intelligence.confidence import score_confidence, to_band
from app.services.intelligence.schemas import ConfidenceBand

__all__ = [
    "ConfidenceBand",
    "presets",
    "score_confidence",
    "to_band",
]
