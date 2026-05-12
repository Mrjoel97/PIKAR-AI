# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: customer-support instructions.md exists and preserves persona content."""

from pathlib import Path

INSTRUCTIONS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "customer_support"
    / "instructions.md"
)


def test_instructions_file_exists_and_non_empty():
    assert INSTRUCTIONS_PATH.exists()
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    assert len(body.strip()) > 1500


def test_instructions_preserves_core_capability_markers():
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    for marker in [
        "Customer Success Manager",
        "ticket_sentiment_analysis",
        "churn_risk_indicators",
        "kb_article_templates",
        "escalation_framework",
        "first_response_templates",
        "create_ticket",
        "draft_customer_response",
        "suggest_faq_from_tickets",
        "get_customer_health_dashboard",
        "create_ticket_from_channel",
        "BEHAVIOR",
        "ESCALATION",
    ]:
        assert marker in body, f"instructions.md missing required marker: {marker!r}"
