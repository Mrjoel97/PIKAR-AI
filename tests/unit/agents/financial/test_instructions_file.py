# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: financial instructions.md exists and preserves persona content."""

from pathlib import Path


INSTRUCTIONS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "financial"
    / "instructions.md"
)


def test_instructions_file_exists_and_non_empty():
    assert INSTRUCTIONS_PATH.exists(), f"missing {INSTRUCTIONS_PATH}"
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    assert len(body.strip()) > 500, "instructions.md is suspiciously short"


def test_instructions_preserves_core_capability_markers():
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    # These markers come from the existing FINANCIAL_AGENT_INSTRUCTION string;
    # extraction must preserve them verbatim so behavior is unchanged.
    for marker in [
        "Financial Analysis Agent",
        "get_revenue_stats",
        "analyze_financial_statement",
        "FINANCIAL HEALTH SCORE",
        "SCENARIO MODELING",
        "FINANCIAL FORECASTING",
        "CONNECTED FINANCIAL DATA",
        "INVOICE FOLLOW-UP",
        "TAX AWARENESS",
        "INPUT VALIDATION",
        "FINANCIAL RISK ALERTS",
    ]:
        assert marker in body, f"instructions.md missing required marker: {marker!r}"
