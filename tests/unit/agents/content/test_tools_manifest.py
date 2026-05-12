# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: the content tool manifest resolves every tool to a real callable."""

from pathlib import Path

from app.agents.content.tools import _TOOL_IDS, build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.tools_manifest import ToolsManifest

OPS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "content"
    / "operations.yaml"
)


def test_manifest_returns_tools_manifest_instance():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    assert isinstance(manifest, ToolsManifest)
    assert manifest.tool_ids, "manifest must declare at least one tool id"


def test_manifest_includes_core_content_tools():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    for required in [
        "simple_create_content",
        "suggest_and_schedule_content",
        "learn_brand_voice",
        "get_content_performance",
        "process_brain_dump",
        "start_content_pipeline",
        "knowledge",
        "brand_profile",
        "creative_brief",
        "art_direction",
        "context_memory",
        "document_gen",
        "ui_widgets",
    ]:
        assert required in manifest.tool_ids, (
            f"manifest missing required tool: {required}"
        )


def test_manifest_resolves_every_id_to_a_callable():
    """Every declared id must resolve via ToolsManifest.resolve() to a callable."""
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    assert len(resolved) == len(manifest.tool_ids), (
        "resolve() must return one callable per declared id"
    )
    for tool in resolved:
        assert callable(tool), f"resolved entry is not callable: {tool!r}"


def test_tool_ids_constant_is_stable():
    """The static tool list is the source of truth — ops only narrows it."""
    assert isinstance(_TOOL_IDS, list)
    # Content is the most complex W4 pilot; 20+ ids is realistic.
    assert len(_TOOL_IDS) >= 15


def test_manifest_resolves_local_callables_first():
    """Local content callables (simple_create_content, etc.) must resolve to the
    real functions defined / re-exported in app.agents.content.tools — not to
    placeholders or shared-module surrogates."""
    from app.agents.content.tools import (
        get_braindump_document,
        get_content_performance,
        get_pipeline_status,
        learn_brand_voice,
        list_content_pipelines,
        process_brain_dump,
        process_brainstorm_conversation,
        simple_create_content,
        start_content_pipeline,
        suggest_and_schedule_content,
        update_pipeline_stage,
    )

    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()

    by_id = dict(zip(manifest.tool_ids, resolved, strict=True))
    assert by_id["simple_create_content"] is simple_create_content
    assert by_id["suggest_and_schedule_content"] is suggest_and_schedule_content
    assert by_id["learn_brand_voice"] is learn_brand_voice
    assert by_id["get_content_performance"] is get_content_performance
    assert by_id["process_brain_dump"] is process_brain_dump
    assert by_id["process_brainstorm_conversation"] is process_brainstorm_conversation
    assert by_id["get_braindump_document"] is get_braindump_document
    assert by_id["start_content_pipeline"] is start_content_pipeline
    assert by_id["update_pipeline_stage"] is update_pipeline_stage
    assert by_id["get_pipeline_status"] is get_pipeline_status
    assert by_id["list_content_pipelines"] is list_content_pipelines
