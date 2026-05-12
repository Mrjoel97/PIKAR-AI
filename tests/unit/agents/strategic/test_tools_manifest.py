# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: the strategic tool manifest resolves every tool to a real callable."""

from pathlib import Path

from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.tools_manifest import ToolsManifest
from app.agents.strategic.tools import _TOOL_IDS, build_tools_manifest

OPS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "strategic"
    / "strategic.yaml"
)


def test_manifest_returns_tools_manifest_instance():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    assert isinstance(manifest, ToolsManifest)
    assert manifest.tool_ids


def test_manifest_includes_core_strategic_tools():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    for required in [
        # Initiative CRUD.
        "create_initiative",
        "get_initiative",
        "update_initiative",
        "list_initiatives",
        # Initiative lifecycle.
        "start_initiative_from_idea",
        "advance_initiative_phase",
        "list_initiative_templates",
        "create_initiative_from_template",
        "start_journey_workflow",
        "suggest_workflows",
        "journey_metrics",
        # Brain dump processing.
        "get_braindump_document",
        "process_brain_dump",
        "process_brainstorm_conversation",
        # Strategic-specific.
        "convene_board_meeting",
        "create_operational_skill",
        "product_roadmap_guide",
        # Workflow integration.
        "orchestrate_initiative_phase",
        "approve_workflow_step",
        "get_workflow_status",
        # Web research.
        "mcp_web_search",
        "mcp_web_scrape",
        # Shared packs.
        "briefing_tools",
        "adaptive_workflows",
        "ui_widgets",
        "context_memory",
        "graph_tools",
        "system_knowledge",
        "document_gen",
    ]:
        assert required in manifest.tool_ids, (
            f"manifest missing required tool: {required}"
        )


def test_manifest_resolves_every_id_to_a_callable():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    assert len(resolved) == len(manifest.tool_ids)
    for tool in resolved:
        assert callable(tool)


def test_tool_ids_constant_is_stable():
    assert isinstance(_TOOL_IDS, list)
    # 22 local + 7 shared packs = 29 (subject to evolution; this guards the
    # lower bound against accidental deletions).
    assert len(_TOOL_IDS) >= 25


def test_manifest_resolves_local_callables_first():
    """Every local strategic callable must resolve off this module's
    namespace, not off the shared registry."""
    from app.agents.strategic.tools import (
        advance_initiative_phase,
        approve_workflow_step,
        convene_board_meeting,
        create_initiative,
        create_initiative_from_template,
        create_operational_skill,
        get_braindump_document,
        get_initiative,
        get_workflow_status,
        journey_metrics,
        list_initiative_templates,
        list_initiatives,
        mcp_web_scrape,
        mcp_web_search,
        orchestrate_initiative_phase,
        process_brain_dump,
        process_brainstorm_conversation,
        product_roadmap_guide,
        start_initiative_from_idea,
        start_journey_workflow,
        suggest_workflows,
        update_initiative,
    )

    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    by_id = dict(zip(manifest.tool_ids, resolved, strict=True))

    assert by_id["create_initiative"] is create_initiative
    assert by_id["get_initiative"] is get_initiative
    assert by_id["update_initiative"] is update_initiative
    assert by_id["list_initiatives"] is list_initiatives
    assert by_id["start_initiative_from_idea"] is start_initiative_from_idea
    assert by_id["advance_initiative_phase"] is advance_initiative_phase
    assert by_id["list_initiative_templates"] is list_initiative_templates
    assert by_id["create_initiative_from_template"] is create_initiative_from_template
    assert by_id["start_journey_workflow"] is start_journey_workflow
    assert by_id["suggest_workflows"] is suggest_workflows
    assert by_id["journey_metrics"] is journey_metrics
    assert by_id["get_braindump_document"] is get_braindump_document
    assert by_id["process_brain_dump"] is process_brain_dump
    assert by_id["process_brainstorm_conversation"] is process_brainstorm_conversation
    assert by_id["convene_board_meeting"] is convene_board_meeting
    assert by_id["create_operational_skill"] is create_operational_skill
    assert by_id["product_roadmap_guide"] is product_roadmap_guide
    assert by_id["orchestrate_initiative_phase"] is orchestrate_initiative_phase
    assert by_id["approve_workflow_step"] is approve_workflow_step
    assert by_id["get_workflow_status"] is get_workflow_status
    assert by_id["mcp_web_search"] is mcp_web_search
    assert by_id["mcp_web_scrape"] is mcp_web_scrape
