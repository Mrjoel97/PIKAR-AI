# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract tests for the financial pilot (Task 111).

Verifies the four invariants the W2 plan calls out for every pilot agent:

1. ``operations.yaml`` parses cleanly via :meth:`OperationsConfig.load`.
2. Every tool name in :func:`build_tools_manifest`'s manifest resolves to
   a real callable (or a documented placeholder for an in-flight pack).
3. ``instructions.md`` exists, is non-empty, and carries the key persona
   markers from the legacy ``FINANCIAL_AGENT_INSTRUCTION`` string.
4. Every pattern in ``ops.skills.allowed_ids`` matches at least one
   skill in :data:`skills_registry`.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from app.agents.financial.tools import _TOOL_IDS, build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.skills.registry import skills_registry

_FIN_DIR = (
    Path(__file__).resolve().parents[4] / "app" / "agents" / "financial"
)
OPS_PATH = _FIN_DIR / "operations.yaml"
INSTRUCTIONS_PATH = _FIN_DIR / "instructions.md"


# ---------------------------------------------------------------------------
# 1. operations.yaml parses
# ---------------------------------------------------------------------------


def test_operations_yaml_parses_cleanly():
    ops = OperationsConfig.load(OPS_PATH)
    assert ops.agent_id == "financial"
    # Smoke: every nested section materialized via OperationsConfig defaults
    # at minimum, plus the values authored by Task 107.
    assert ops.skills.allowed_ids
    assert ops.initiative.phases_owned


# ---------------------------------------------------------------------------
# 2. Tool manifest resolves to real callables
# ---------------------------------------------------------------------------


def test_every_tool_id_resolves_to_callable():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    assert len(resolved) == len(manifest.tool_ids)
    for tool_id, fn in zip(manifest.tool_ids, resolved, strict=True):
        assert callable(fn), f"tool id {tool_id!r} did not resolve to a callable"


def test_every_tool_id_has_a_real_implementation():
    """No declared tool id should silently fall through to a placeholder.

    The :class:`ToolsManifest` resolver wraps unresolved ids in a no-op
    placeholder (tagged with ``missing_tool_id``) so the manifest stays
    well-formed; this contract test fails the build if any financial tool
    falls into that branch, surfacing a missing import or renamed module.
    """
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
    """The static ``_TOOL_IDS`` list is the canonical source of truth."""
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    assert list(manifest.tool_ids) == list(_TOOL_IDS)


# ---------------------------------------------------------------------------
# 3. instructions.md carries persona markers
# ---------------------------------------------------------------------------


def test_instructions_present_and_non_empty():
    assert INSTRUCTIONS_PATH.exists()
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    assert body.strip(), "instructions.md is empty"


def test_instructions_preserves_key_persona_markers():
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    for marker in [
        "Financial Analysis Agent",
        "get_revenue_stats",
        "FINANCIAL HEALTH SCORE",
        "SCENARIO MODELING",
        "FINANCIAL FORECASTING",
    ]:
        assert marker in body, f"instructions.md missing marker {marker!r}"


# ---------------------------------------------------------------------------
# 4. skills.allowed_ids patterns match real skills
# ---------------------------------------------------------------------------


def _flat_skill_ids() -> list[str]:
    """Return canonical skill ids as ``{category}:{name}`` strings."""
    return [f"{skill.category}:{skill.name}" for skill in skills_registry.list_all()]


def test_every_allowed_id_pattern_matches_at_least_one_skill():
    ops = OperationsConfig.load(OPS_PATH)
    flat = _flat_skill_ids()
    assert flat, "skills_registry returned no skills — fixture missing"

    unmatched: list[str] = []
    for pattern in ops.skills.allowed_ids:
        if not any(fnmatch.fnmatch(skill_id, pattern) for skill_id in flat):
            unmatched.append(pattern)

    assert not unmatched, (
        f"operations.yaml declares skill patterns with zero matches: {unmatched}"
    )


def test_finance_wildcard_matches_canonical_finance_skills():
    """Tasks 106/107 reference these skill names; the registry must still
    expose them or the agent's persona instructions go stale."""
    ops = OperationsConfig.load(OPS_PATH)
    flat = _flat_skill_ids()
    finance_hits = [s for s in flat if fnmatch.fnmatch(s, "finance:*")]
    expected = {
        "finance:financial_statements_generation",
        "finance:variance_analysis",
        "finance:journal_entry_preparation",
        "finance:month_end_close_management",
        "finance:account_reconciliation",
        "finance:sox_testing_methodology",
        "finance:audit_support_framework",
    }
    missing = expected - set(finance_hits)
    assert not missing, f"finance skills disappeared from registry: {missing}"
    assert any(p == "finance:*" for p in ops.skills.allowed_ids)
