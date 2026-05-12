# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: the sales tool manifest resolves every tool to a real callable."""

from pathlib import Path

from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.tools_manifest import ToolsManifest
from app.agents.sales.tools import _TOOL_IDS, build_tools_manifest

OPS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "sales"
    / "operations.yaml"
)


def test_manifest_returns_tools_manifest_instance():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    assert isinstance(manifest, ToolsManifest)
    assert manifest.tool_ids


def test_manifest_includes_core_sales_tools():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    for required in [
        "create_task",
        "get_task",
        "update_task",
        "list_tasks",
        "hubspot_tools",
        "ui_widgets",
        "context_memory",
        "document_gen",
        "calendar_tool",
        "pipeline_dashboard",
        "sales_followup",
        "proposal_generator",
        "quick_research",
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
        assert callable(tool), f"resolved entry is not callable: {tool!r}"


def test_tool_ids_constant_is_stable():
    assert isinstance(_TOOL_IDS, list)
    assert len(_TOOL_IDS) >= 12


def test_manifest_resolves_local_callables_first():
    from app.agents.sales.tools import create_task, get_task, list_tasks, update_task

    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    by_id = dict(zip(manifest.tool_ids, resolved, strict=True))

    assert by_id["create_task"] is create_task
    assert by_id["get_task"] is get_task
    assert by_id["update_task"] is update_task
    assert by_id["list_tasks"] is list_tasks
