# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: content instructions.md exists and preserves persona content."""

from pathlib import Path

INSTRUCTIONS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "content"
    / "instructions.md"
)


def test_instructions_file_exists_and_non_empty():
    assert INSTRUCTIONS_PATH.exists(), f"missing {INSTRUCTIONS_PATH}"
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    # Content's director prompt is substantial (~10KB legacy). Set a low
    # floor that still catches truncation regressions.
    assert len(body.strip()) > 2000, "instructions.md is suspiciously short"


def test_instructions_preserves_core_capability_markers():
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    # These markers come from the existing CONTENT_DIRECTOR_INSTRUCTION
    # string; extraction must preserve them verbatim so behavior is
    # unchanged when the agent loads its prompt from disk.
    for marker in [
        "Content Director",
        "VideoDirectorAgent",
        "GraphicDesignerAgent",
        "CopywriterAgent",
        "simple_create_content",
        "ONE-SHOT FAST PATH",
        "DIRECT VIDEO REQUESTS",
        "CREATIVE PIPELINE",
        "FULL CONTENT PIPELINE",
        "CRITICAL: CONTEXT AWARENESS",
        "BRAIN DUMP",
        "BRANDED DOCUMENT GENERATION",
        "generate_pdf_report",
        "generate_pitch_deck",
        "generate_spreadsheet_workbook",
        "DELEGATION STRATEGY",
        "DIRECT SOCIAL POSTING",
        "publish_to_social",
        "CONTENT QUALITY GATES",
        "CONTENT FAILURE FALLBACKS",
        "POST-CREATION SCHEDULING",
        "suggest_and_schedule_content",
        "BRAND VOICE AUTO-LEARNING",
        "learn_brand_voice",
        "CONTENT PERFORMANCE FEEDBACK LOOP",
        "get_content_performance",
        "Editing Documents",
        "read_document_content",
    ]:
        assert marker in body, f"instructions.md missing required marker: {marker!r}"
