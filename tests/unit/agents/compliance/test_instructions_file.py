# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: compliance instructions.md exists and preserves persona content."""

from pathlib import Path

INSTRUCTIONS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "compliance"
    / "instructions.md"
)


def test_instructions_file_exists_and_non_empty():
    assert INSTRUCTIONS_PATH.exists()
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    assert len(body.strip()) > 3000


def test_instructions_preserves_core_capability_markers():
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    for marker in [
        "Compliance & Risk Agent",
        "gdpr_audit_checklist",
        "risk_assessment_matrix",
        "ccpa_compliance_checklist",
        "sox_compliance_framework",
        "hipaa_compliance_checklist",
        "contract_review_framework",
        "nda_triage",
        "legal_risk_assessment",
        "STRUCTURED RISK REPORTS",
        "RiskReportAgent",
        "get_compliance_health_score",
        "generate_legal_document",
        "explain_contract_clause",
        "create_deadline",
        "check_regulatory_updates",
        "ESCALATION",
    ]:
        assert marker in body, f"instructions.md missing required marker: {marker!r}"
