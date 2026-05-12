# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: the customer-support tool manifest resolves every tool to a real callable."""

from pathlib import Path

from app.agents.customer_support.tools import _TOOL_IDS, build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.tools_manifest import ToolsManifest

OPS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "customer_support"
    / "operations.yaml"
)


def test_manifest_returns_tools_manifest_instance():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    assert isinstance(manifest, ToolsManifest)
    assert manifest.tool_ids


def test_manifest_includes_core_customer_support_tools():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    for required in [
        "create_ticket",
        "get_ticket",
        "list_tickets",
        "draft_customer_response",
        "suggest_faq_from_tickets",
        "get_customer_health_dashboard",
        "create_ticket_from_channel",
        "knowledge",
        "ui_widgets",
        "context_memory",
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
        assert callable(tool), f"resolved entry is not callable: {tool!r}"


def test_tool_ids_constant_is_stable():
    assert isinstance(_TOOL_IDS, list)
    assert len(_TOOL_IDS) >= 12


def test_manifest_resolves_local_callables_first():
    from app.agents.customer_support.tools import (
        create_ticket,
        create_ticket_from_channel,
        draft_customer_response,
        get_customer_health_dashboard,
        get_ticket,
        list_tickets,
        suggest_faq_from_tickets,
        update_ticket,
    )

    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    by_id = dict(zip(manifest.tool_ids, resolved, strict=True))

    assert by_id["create_ticket"] is create_ticket
    assert by_id["get_ticket"] is get_ticket
    assert by_id["update_ticket"] is update_ticket
    assert by_id["list_tickets"] is list_tickets
    assert by_id["draft_customer_response"] is draft_customer_response
    assert by_id["suggest_faq_from_tickets"] is suggest_faq_from_tickets
    assert by_id["get_customer_health_dashboard"] is get_customer_health_dashboard
    assert by_id["create_ticket_from_channel"] is create_ticket_from_channel
