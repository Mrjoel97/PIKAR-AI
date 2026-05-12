# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: HR instructions.md exists and preserves persona content."""

from pathlib import Path

INSTRUCTIONS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "hr"
    / "instructions.md"
)


def test_instructions_file_exists_and_non_empty():
    assert INSTRUCTIONS_PATH.exists()
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    assert len(body.strip()) > 1500


def test_instructions_preserves_core_capability_markers():
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    for marker in [
        "HR & Recruitment Agent",
        "resume_screening",
        "interview_question_generator",
        "BIAS & FAIRNESS GUARDRAILS",
        "Evaluate ONLY on job-relevant competencies",
        "INTERVIEW FRAMEWORK",
        "STAR method",
        "INPUT VALIDATION",
        "generate_job_description",
        "generate_interview_questions",
        "get_hiring_funnel",
        "auto_generate_onboarding",
        "get_team_org_chart",
        "ESCALATION",
    ]:
        assert marker in body, f"instructions.md missing required marker: {marker!r}"
