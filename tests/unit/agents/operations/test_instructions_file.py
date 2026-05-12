# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: operations instructions.md exists and preserves persona content."""

from pathlib import Path

INSTRUCTIONS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "operations"
    / "instructions.md"
)


def test_instructions_file_exists_and_non_empty():
    assert INSTRUCTIONS_PATH.exists()
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    assert len(body.strip()) > 5000


def test_instructions_preserves_core_capability_markers():
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    for marker in [
        "Operations Optimization Agent",
        "Autonomous Skill Creation",
        "create_operational_skill",
        "security_checklist",
        "cloud_architecture_guide",
        "container_deployment_guide",
        "process_bottleneck_analysis",
        "sop_generation",
        "PROJECT MANAGEMENT INTEGRATION",
        "get_pm_projects",
        "create_pm_task",
        "NOTIFICATION MANAGEMENT",
        "send_notification_to_channel",
        "OUTBOUND WEBHOOKS",
        "create_webhook_endpoint",
        "WORKFLOW BOTTLENECK DETECTION",
        "analyze_workflow_bottlenecks",
        "SOP GENERATION",
        "generate_sop_document",
        "VENDOR/SAAS COST TRACKING",
        "ESCALATION",
    ]:
        assert marker in body, f"instructions.md missing required marker: {marker!r}"
