# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: strategic instructions.md exists and preserves persona content."""

from pathlib import Path

INSTRUCTIONS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "strategic"
    / "instructions.md"
)


def test_instructions_file_exists_and_non_empty():
    assert INSTRUCTIONS_PATH.exists()
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    assert len(body.strip()) > 3000


def test_instructions_preserves_core_capability_markers():
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    for marker in [
        "Strategic Planning Agent",
        "INITIATIVE FRAMEWORK",
        "Ideation",
        "Validation",
        "Prototype",
        "Build",
        "Scale",
        "AUTO-INITIATIVE DETECTION",
        "start_initiative_from_idea",
        "BRAIN DUMP",
        "BraindumpPipeline",
        "process_brainstorm_conversation",
        "get_braindump_document",
        "ELITE RESEARCH SUITE",
        "ResearchSuite",
        "MarketAnalystAgent",
        "CompetitiveResearcherAgent",
        "ConsumerExpertAgent",
        "convene_board_meeting",
        "create_operational_skill",
        "product_roadmap_guide",
        "INITIATIVE QUALITY GATES",
        "ESCALATION",
    ]:
        assert marker in body, f"instructions.md missing required marker: {marker!r}"
