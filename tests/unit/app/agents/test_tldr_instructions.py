# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for TL;DR response instruction constant.

Uses importlib to load shared_instructions directly, avoiding the heavy
app.agents.__init__ import chain that requires google-adk and supabase.
"""

import importlib.util
from pathlib import Path

_MOD_PATH = Path(__file__).resolve().parents[4] / "app" / "agents" / "shared_instructions.py"
_spec = importlib.util.spec_from_file_location("shared_instructions", _MOD_PATH)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

TLDR_RESPONSE_INSTRUCTIONS: str = _mod.TLDR_RESPONSE_INSTRUCTIONS  # type: ignore[attr-defined]


class TestTldrResponseInstructions:
    """Verify TLDR_RESPONSE_INSTRUCTIONS is well-formed and importable."""

    def test_contains_delimiters(self) -> None:
        """TL;DR instruction must contain the exact start/end delimiters."""
        assert "---TLDR---" in TLDR_RESPONSE_INSTRUCTIONS
        assert "---END_TLDR---" in TLDR_RESPONSE_INSTRUCTIONS

    def test_contains_required_fields(self) -> None:
        """TL;DR instruction must reference all three structured fields."""
        assert "**Summary:**" in TLDR_RESPONSE_INSTRUCTIONS
        assert "**Key Number:**" in TLDR_RESPONSE_INSTRUCTIONS
        assert "**Next Step:**" in TLDR_RESPONSE_INSTRUCTIONS

    def test_constant_is_nonempty_string(self) -> None:
        """The constant must be a non-empty string."""
        assert isinstance(TLDR_RESPONSE_INSTRUCTIONS, str)
        assert len(TLDR_RESPONSE_INSTRUCTIONS.strip()) > 0
