# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract tests for the HR agent (W4 migration)."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from app.agents.hr.tools import _TOOL_IDS, build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.skills.registry import skills_registry

_HR_DIR = Path(__file__).resolve().parents[4] / "app" / "agents" / "hr"
OPS_PATH = _HR_DIR / "operations.yaml"
INSTRUCTIONS_PATH = _HR_DIR / "instructions.md"


def test_operations_yaml_parses_cleanly():
    ops = OperationsConfig.load(OPS_PATH)
    assert ops.agent_id == "hr"
    assert ops.skills.allowed_ids
    assert ops.initiative.phases_owned


def test_every_tool_id_resolves_to_callable():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    assert len(resolved) == len(manifest.tool_ids)
    for tool_id, fn in zip(manifest.tool_ids, resolved, strict=True):
        assert callable(fn), f"tool id {tool_id!r} did not resolve to a callable"


def test_every_tool_id_has_a_real_implementation():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    missing = [
        tid
        for tid, fn in zip(manifest.tool_ids, resolved, strict=True)
        if getattr(fn, "missing_tool_id", None) is not None
    ]
    assert not missing, f"tool ids resolved to placeholder: {missing}"


def test_tool_ids_constant_matches_manifest():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    assert list(manifest.tool_ids) == list(_TOOL_IDS)


def test_instructions_present_and_non_empty():
    assert INSTRUCTIONS_PATH.exists()
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    assert body.strip()


def test_instructions_preserves_key_persona_markers():
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    for marker in [
        "HR & Recruitment Agent",
        "BIAS & FAIRNESS GUARDRAILS",
        "INTERVIEW FRAMEWORK",
        "generate_job_description",
        "generate_interview_questions",
        "STAR method",
        "get_team_org_chart",
        "post_job_board",
        "auto_generate_onboarding",
        "INPUT VALIDATION",
        "ESCALATION",
    ]:
        assert marker in body, f"instructions.md missing marker {marker!r}"


def _flat_skill_ids() -> list[str]:
    return [f"{skill.category}:{skill.name}" for skill in skills_registry.list_all()]


def test_every_allowed_id_pattern_matches_at_least_one_skill():
    ops = OperationsConfig.load(OPS_PATH)
    flat = _flat_skill_ids()
    assert flat

    unmatched: list[str] = []
    for pattern in ops.skills.allowed_ids:
        if not any(fnmatch.fnmatch(skill_id, pattern) for skill_id in flat):
            unmatched.append(pattern)

    assert not unmatched, (
        f"operations.yaml declares skill patterns with zero matches: {unmatched}"
    )


def test_hr_wildcard_matches_canonical_hr_skills():
    ops = OperationsConfig.load(OPS_PATH)
    flat = _flat_skill_ids()
    hr_hits = [s for s in flat if fnmatch.fnmatch(s, "hr:*")]
    assert hr_hits, (
        "no skills with category=hr; the hr:* wildcard would resolve to nothing"
    )
    assert any(p == "hr:*" for p in ops.skills.allowed_ids)
