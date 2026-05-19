"""Per-agent confidence presets.

Each preset is a thin wrapper over score_confidence with domain-specific
input mapping and weights. Add a new preset when a new agent class needs
its own formula — Phase 113 adds data_confidence.
"""

from app.services.intelligence.presets.research import research_confidence

__all__ = ["research_confidence"]
