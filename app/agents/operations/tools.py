# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tools manifest for the Operations Optimization Agent (W4 migration).

Operations doesn't own its own per-agent tool callables — it reuses task
tools from ``app.agents.sales.tools`` and singleton tools from
``app.agents.enhanced_tools`` + ``app.agents.tools.skill_builder``.

The re-exports below are load-bearing: the
:class:`~app.agents.runtime.tools_manifest.ToolsManifest` resolver looks
up tool ids against this module first (``local_tools_module``), then
falls through to ``app.agents.tools.<id>``. Without these re-exports
the cross-agent + enhanced-tools surface would resolve to placeholders.

The ``# noqa: F401`` markers stop ruff's auto-fix from stripping these
imports during a routine format pass.
"""

from app.agents.enhanced_tools import (
    audit_user_setup_tool,  # noqa: F401
    cloud_architecture_guide,  # noqa: F401
    container_deployment_guide,  # noqa: F401
    security_checklist,  # noqa: F401
)
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.tools_manifest import ToolsManifest
from app.agents.sales.tools import (
    create_task,  # noqa: F401
    get_task,  # noqa: F401
    list_tasks,  # noqa: F401
    update_task,  # noqa: F401
)
from app.agents.tools.skill_builder import create_operational_skill  # noqa: F401


# =============================================================================
# Tools manifest — declarative tool surface for PikarBaseAgent factory.
# =============================================================================

_TOOL_IDS: list[str] = [
    # Local re-exports resolved against this module via _try_local.
    "create_operational_skill",
    "create_task",
    "get_task",
    "update_task",
    "list_tasks",
    "security_checklist",
    "container_deployment_guide",
    "cloud_architecture_guide",
    # Shared tool packs under ``app.agents.tools.<id>``.
    "ui_widgets",
    "context_memory",
    "graph_tools",
    "system_knowledge",
    "document_gen",
    "calendar_tool",
    "pm_task_tools",
    "communication_tools",
    "webhook_tools",
    "inventory",
    "ops_tools",
    "quick_research",
]


def build_tools_manifest(ops: OperationsConfig) -> ToolsManifest:
    """Build the operations director tool manifest.

    Note: the legacy code explicitly filtered ``create_app_builder_launcher_widget``
    and ``create_app_builder_canvas_widget`` out of UI_WIDGET_TOOLS for
    operations (App Builder is owned by ExecutiveAgent). The manifest
    pack-based model exposes the full UI_WIDGET_TOOLS list as a single
    ``_ToolPack`` — App Builder gating is now enforced at the tool layer
    rather than the per-agent toolset.
    """
    _ = ops  # reserved for future per-persona filtering
    return ToolsManifest(
        tool_ids=list(_TOOL_IDS),
        local_tools_module=__name__,
    )
