"""Tests for the INTENT_CLARIFICATION_INSTRUCTIONS constant.

Verifies that the intent clarification protocol contains the required
delimiters, option markers, and is importable as a string constant.

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

INTENT_CLARIFICATION_INSTRUCTIONS: str = _mod.INTENT_CLARIFICATION_INSTRUCTIONS  # type: ignore[attr-defined]


class TestIntentClarificationInstructions:
    """Validate the INTENT_CLARIFICATION_INSTRUCTIONS constant."""

    def test_contains_required_delimiters(self) -> None:
        """The instruction must include the exact start/end delimiters."""
        assert "---INTENT_OPTIONS---" in INTENT_CLARIFICATION_INSTRUCTIONS
        assert "---END_OPTIONS---" in INTENT_CLARIFICATION_INSTRUCTIONS

    def test_contains_option_markers(self) -> None:
        """The instruction must include [OPTION_1], [OPTION_2], [OPTION_3] examples."""
        assert "[OPTION_1]" in INTENT_CLARIFICATION_INSTRUCTIONS
        assert "[OPTION_2]" in INTENT_CLARIFICATION_INSTRUCTIONS
        assert "[OPTION_3]" in INTENT_CLARIFICATION_INSTRUCTIONS

    def test_is_nonempty_string(self) -> None:
        """The constant must be a non-empty string."""
        assert isinstance(INTENT_CLARIFICATION_INSTRUCTIONS, str)
        assert len(INTENT_CLARIFICATION_INSTRUCTIONS.strip()) > 100
