# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Verify the runtime package exposes the gate/audit/persona/router public API."""

from __future__ import annotations

import app.agents.runtime as runtime


def test_research_gate_api_exposed() -> None:
    for name in (
        "RESEARCH_TOOL_IDS",
        "open_gate",
        "is_open",
        "record_tool_result",
        "check_coverage",
        "close_gate",
    ):
        assert hasattr(runtime, name), name


def test_audit_api_exposed() -> None:
    for name in (
        "audit_against_contract",
        "persist_audit_report",
        "attach_audit_summary_to_evidence",
    ):
        assert hasattr(runtime, name), name


def test_persona_gate_api_exposed() -> None:
    for name in (
        "load_persona_policy",
        "check_tool_allowed",
        "check_action_threshold",
        "apply_prompt_fragments",
        "record_violation",
    ):
        assert hasattr(runtime, name), name


def test_task_router_api_exposed() -> None:
    for name in ("classify", "DIRECT_VERBS", "INITIATIVE_VERBS", "DIRECT_LENGTH_THRESHOLD"):
        assert hasattr(runtime, name), name
