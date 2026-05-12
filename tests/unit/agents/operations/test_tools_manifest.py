# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: the operations tool manifest resolves every tool to a real callable."""

from pathlib import Path

from app.agents.operations.tools import _TOOL_IDS, build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.tools_manifest import ToolsManifest

OPS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "operations"
    / "operations.yaml"
)


def test_manifest_returns_tools_manifest_instance():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    assert isinstance(manifest, ToolsManifest)
    assert manifest.tool_ids


def test_manifest_includes_core_operations_tools():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    for required in [
        "create_operational_skill",
        "create_task",
        "get_task",
        "list_tasks",
        "security_checklist",
        "container_deployment_guide",
        "cloud_architecture_guide",
        "ui_widgets",
        "context_memory",
        "pm_task_tools",
        "communication_tools",
        "webhook_tools",
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
    assert len(_TOOL_IDS) >= 15


def test_manifest_resolves_local_callables_first():
    """Cross-agent re-exports (create_task, etc.) must resolve to the
    sales-tools originals via this module's re-import path."""
    from app.agents.operations.tools import (
        cloud_architecture_guide,
        container_deployment_guide,
        create_operational_skill,
        create_task,
        get_task,
        list_tasks,
        security_checklist,
        update_task,
    )

    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    by_id = dict(zip(manifest.tool_ids, resolved, strict=True))

    assert by_id["create_task"] is create_task
    assert by_id["get_task"] is get_task
    assert by_id["update_task"] is update_task
    assert by_id["list_tasks"] is list_tasks
    assert by_id["security_checklist"] is security_checklist
    assert by_id["container_deployment_guide"] is container_deployment_guide
    assert by_id["cloud_architecture_guide"] is cloud_architecture_guide
    assert by_id["create_operational_skill"] is create_operational_skill
