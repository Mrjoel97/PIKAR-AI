# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: sales instructions.md exists and preserves persona content."""

from pathlib import Path

INSTRUCTIONS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "sales"
    / "instructions.md"
)


def test_instructions_file_exists_and_non_empty():
    assert INSTRUCTIONS_PATH.exists()
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    assert len(body.strip()) > 2000


def test_instructions_preserves_core_capability_markers():
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    for marker in [
        "Sales Intelligence Agent",
        "lead_qualification_framework",
        "BANT",
        "MEDDIC",
        "CHAMP",
        "STRUCTURED LEAD SCORING",
        "LeadScoringAgent",
        "CRM-AWARE BEHAVIOR",
        "get_hubspot_deal_context",
        "AUTO-SYNC BEHAVIOR",
        "sync_deal_notes",
        "PIPELINE HEALTH DASHBOARD",
        "POST-MEETING FOLLOW-UP",
        "generate_followup_email",
        "PROPOSAL GENERATION",
        "generate_sales_proposal",
        "ESCALATION",
    ]:
        assert marker in body, f"instructions.md missing required marker: {marker!r}"
