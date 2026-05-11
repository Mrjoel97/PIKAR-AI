# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: the financial tool manifest resolves every tool to a real callable."""

from pathlib import Path

from app.agents.financial.tools import _TOOL_IDS, build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.tools_manifest import ToolsManifest

OPS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "financial"
    / "operations.yaml"
)


def test_manifest_returns_tools_manifest_instance():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    assert isinstance(manifest, ToolsManifest)
    assert manifest.tool_ids, "manifest must declare at least one tool id"


def test_manifest_includes_core_finance_tools():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    for required in [
        "get_revenue_stats",
        "get_financial_health_score",
        "run_financial_scenario",
        "generate_financial_forecast",
        "invoicing",
        "deep_research",
        "knowledge",
        "approval_tool",
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
    assert len(_TOOL_IDS) >= 8


def test_manifest_resolves_local_callables_first():
    """Local finance callables (get_revenue_stats, ...) must resolve to the
    real functions defined in app.agents.financial.tools — not to placeholders
    or shared-module surrogates."""
    from app.agents.financial.tools import (
        generate_financial_forecast,
        get_financial_health_score,
        get_revenue_stats,
        run_financial_scenario,
    )

    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()

    by_id = dict(zip(manifest.tool_ids, resolved, strict=True))
    assert by_id["get_revenue_stats"] is get_revenue_stats
    assert by_id["get_financial_health_score"] is get_financial_health_score
    assert by_id["run_financial_scenario"] is run_financial_scenario
    assert by_id["generate_financial_forecast"] is generate_financial_forecast
