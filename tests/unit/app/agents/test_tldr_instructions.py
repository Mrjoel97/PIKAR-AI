# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for TL;DR response instruction constant."""

from app.agents.shared_instructions import TLDR_RESPONSE_INSTRUCTIONS


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
