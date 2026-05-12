# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: the compliance tool manifest resolves every tool to a real callable."""

from pathlib import Path

from app.agents.compliance.tools import _TOOL_IDS, build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.tools_manifest import ToolsManifest

OPS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "compliance"
    / "operations.yaml"
)


def test_manifest_returns_tools_manifest_instance():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    assert isinstance(manifest, ToolsManifest)
    assert manifest.tool_ids


def test_manifest_includes_core_compliance_tools():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    for required in [
        "create_audit",
        "create_risk",
        "list_risks",
        "get_compliance_health_score",
        "generate_legal_document",
        "explain_contract_clause",
        "create_deadline",
        "check_regulatory_updates",
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
        assert callable(tool)


def test_tool_ids_constant_is_stable():
    assert isinstance(_TOOL_IDS, list)
    assert len(_TOOL_IDS) >= 18


def test_manifest_resolves_local_callables_first():
    from app.agents.compliance.tools import (
        check_regulatory_updates,
        create_audit,
        create_deadline,
        create_risk,
        explain_contract_clause,
        generate_legal_document,
        get_compliance_health_score,
        list_risks,
    )

    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    by_id = dict(zip(manifest.tool_ids, resolved, strict=True))

    assert by_id["create_audit"] is create_audit
    assert by_id["create_risk"] is create_risk
    assert by_id["list_risks"] is list_risks
    assert by_id["get_compliance_health_score"] is get_compliance_health_score
    assert by_id["generate_legal_document"] is generate_legal_document
    assert by_id["explain_contract_clause"] is explain_contract_clause
    assert by_id["create_deadline"] is create_deadline
    assert by_id["check_regulatory_updates"] is check_regulatory_updates
