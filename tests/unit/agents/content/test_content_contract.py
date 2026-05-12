# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract tests for the content pilot (W4-Pilot).

Verifies the four invariants the W2 plan calls out for every pilot agent:

1. ``operations.yaml`` parses cleanly via :meth:`OperationsConfig.load`.
2. Every tool name in :func:`build_tools_manifest`'s manifest resolves to
   a real callable (or a documented placeholder for an in-flight pack).
3. ``instructions.md`` exists, is non-empty, and carries the key persona
   markers from the legacy ``CONTENT_DIRECTOR_INSTRUCTION`` string.
4. Every pattern in ``ops.skills.allowed_ids`` matches at least one
   skill in :data:`skills_registry`.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from app.agents.content.tools import _TOOL_IDS, build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.skills.registry import skills_registry

_CONT_DIR = Path(__file__).resolve().parents[4] / "app" / "agents" / "content"
OPS_PATH = _CONT_DIR / "operations.yaml"
INSTRUCTIONS_PATH = _CONT_DIR / "instructions.md"


# ---------------------------------------------------------------------------
# 1. operations.yaml parses
# ---------------------------------------------------------------------------


def test_operations_yaml_parses_cleanly():
    ops = OperationsConfig.load(OPS_PATH)
    assert ops.agent_id == "content"
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
    well-formed; this contract test fails the build if any content tool
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
        "Content Director",
        "VideoDirectorAgent",
        "GraphicDesignerAgent",
        "CopywriterAgent",
        "ONE-SHOT FAST PATH",
        "CREATIVE PIPELINE",
        "FULL CONTENT PIPELINE",
        "BRAND VOICE AUTO-LEARNING",
        "CONTENT PERFORMANCE FEEDBACK LOOP",
        "UGC",
        "BRANDED DOCUMENT GENERATION",
        "DIRECT SOCIAL POSTING",
        "POST-CREATION SCHEDULING",
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


def test_content_wildcard_matches_at_least_one_content_skill():
    """The director's primary skill family must remain in the registry."""
    ops = OperationsConfig.load(OPS_PATH)
    flat = _flat_skill_ids()
    content_hits = [s for s in flat if fnmatch.fnmatch(s, "content:*")]
    assert content_hits, (
        "no skills with category=content; the content:* wildcard would resolve to nothing"
    )
    assert any(p == "content:*" for p in ops.skills.allowed_ids)
