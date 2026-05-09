# Copyright (c) 2024-2026 Pikar AI. All rights reserved.

"""Unit tests for the AgentManifest registry (REGISTRY-01..03).

Verifies the declarative registry covers every agent, exposes a stable
helper surface, and that the Executive can be built end-to-end from its
manifest entry.
"""

from __future__ import annotations

import os

import pytest


# Each entry: (registry_key, expected_agent_class_name)
EXPECTED_AGENTS: list[tuple[str, str]] = [
    ("executive", "ExecutiveAgent"),
    ("financial", "FinancialAnalysisAgent"),
    ("content", "ContentCreationAgent"),
    ("strategic", "StrategicPlanningAgent"),
    ("sales", "SalesIntelligenceAgent"),
    ("marketing", "MarketingAutomationAgent"),
    ("operations", "OperationsOptimizationAgent"),
    ("hr", "HRRecruitmentAgent"),
    ("compliance", "ComplianceRiskAgent"),
    ("customer_support", "CustomerSupportAgent"),
    ("data", "DataAnalysisAgent"),
    ("data_reporting", "DataReportingAgent"),
    ("research", "ResearchAgent"),
    ("admin", "AdminAgent"),
]
EXPECTED_KEYS = {key for key, _ in EXPECTED_AGENTS}


# ---------------------------------------------------------------------------
# Manifest registry coverage
# ---------------------------------------------------------------------------


class TestManifestRegistry:
    def test_manifest_module_imports_cleanly(self):
        from app.agents.manifest import MANIFESTS, AgentManifest  # noqa: F401

        assert isinstance(MANIFESTS, dict)

    def test_manifest_registry_covers_all_agents(self):
        from app.agents.manifest import MANIFESTS

        missing = EXPECTED_KEYS - set(MANIFESTS.keys())
        assert not missing, f"Missing manifests: {missing}"

    @pytest.mark.parametrize("key,expected_name", EXPECTED_AGENTS)
    def test_manifest_entry_well_formed(self, key, expected_name):
        from app.agents.manifest import MANIFESTS

        manifest = MANIFESTS[key]
        assert manifest.name == expected_name
        assert manifest.role_definition.strip(), (
            f"{key}: role_definition must be non-empty"
        )
        assert manifest.model_profile in {"routing", "deep", "creative", "fast"}
        assert manifest.config_profile in {"ROUTING", "DEEP", "CREATIVE", "FAST"}

    def test_specialists_have_routing_descriptions(self):
        """Every top-level specialist must declare a routing_description.

        Sub-agents (output_schema reporters, content sub-agents, etc.) and
        the Executive itself are exempt.
        """
        from app.agents.manifest import MANIFESTS

        sub_keys = {
            "executive",
            "financial_report",
            "compliance_risk_report",
            "data_insight",
            "data_report_generator",
            "sales_lead_scoring",
            "content_video_director",
            "content_graphic_designer",
            "content_copywriter",
            "admin",  # admin is platform-management, not an exec specialist
        }
        for key, manifest in MANIFESTS.items():
            if key in sub_keys:
                continue
            assert manifest.routing_description.strip(), (
                f"{key}: top-level specialist needs routing_description"
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestComposeInstruction:
    def test_compose_starts_with_role_definition(self):
        from app.agents.manifest import MANIFESTS, compose_instruction

        manifest = MANIFESTS["financial"]
        rendered = compose_instruction(manifest)

        # Role definition must be the first non-empty line.
        first_line = rendered.lstrip().split("\n", 1)[0]
        assert manifest.role_definition.split(".")[0] in first_line

    def test_compose_includes_tools_section(self):
        from app.agents.manifest import MANIFESTS, compose_instruction

        rendered = compose_instruction(MANIFESTS["financial"])
        assert "## AVAILABLE TOOLS" in rendered

    def test_compose_handles_empty_blocks(self):
        from app.agents.manifest import AgentManifest, compose_instruction

        m = AgentManifest(
            name="DummyAgent",
            role_definition="A dummy role.",
            model_profile="routing",
            config_profile="ROUTING",
        )
        out = compose_instruction(m)
        assert "A dummy role." in out


class TestComposeRoutingTable:
    def test_routing_table_includes_specialists(self):
        from app.agents.manifest import MANIFESTS, compose_routing_table

        table = compose_routing_table(MANIFESTS)
        assert "AVAILABLE SPECIALISTS" in table
        # Spot-check a few specialists with descriptions.
        assert "FinancialAnalysisAgent" in table
        assert "MarketingAutomationAgent" in table
        assert "DataAnalysisAgent" in table

    def test_routing_table_excludes_executive(self):
        from app.agents.manifest import MANIFESTS, compose_routing_table

        table = compose_routing_table(MANIFESTS)
        # The Executive itself should not appear in its own routing list.
        assert "ExecutiveAgent" not in table


class TestResolveToolModules:
    def test_resolves_module_with_tools_export(self):
        """Importing app.agents.tools.context_memory yields a real list."""
        from app.agents.manifest import resolve_tool_modules

        tools = resolve_tool_modules(["app.agents.tools.context_memory"])
        assert isinstance(tools, list)
        assert len(tools) >= 1
        # All entries should be callables.
        assert all(callable(t) for t in tools)

    def test_resolves_named_attribute(self):
        from app.agents.manifest import resolve_tool_modules

        tools = resolve_tool_modules(
            ["app.agents.tools.knowledge:search_knowledge"]
        )
        assert len(tools) == 1
        assert callable(tools[0])

    def test_missing_module_logs_and_skips(self):
        from app.agents.manifest import resolve_tool_modules

        # Should NOT raise; missing modules are logged and skipped.
        out = resolve_tool_modules(["app.agents.does.not.exist"])
        assert out == []


# ---------------------------------------------------------------------------
# Builder smoke test (Executive)
# ---------------------------------------------------------------------------


class TestBuildExecutiveFromManifest:
    def test_build_executive_returns_agent(self):
        from app.agents.manifest import MANIFESTS
        from app.agents.manifest_builder import build_agent

        agent = build_agent(MANIFESTS["executive"])
        assert agent.name == "ExecutiveAgent"
        # Tool count must exceed 30 -- the Executive sweeps the cross-agent
        # tool surface (briefing, deep_research, doc_gen, app_builder, ...).
        assert len(agent.tools) >= 30, (
            f"Executive should have >=30 tools, got {len(agent.tools)}"
        )
        # Sub-agents are populated from the manifest's sub_agents list
        # (12 specialists + executive's structured-JSON sub-agents that the
        # nested builds pull in indirectly).
        assert len(agent.sub_agents) >= 1

    def test_build_executive_with_persona(self):
        from app.agents.manifest import MANIFESTS
        from app.agents.manifest_builder import build_agent

        agent = build_agent(MANIFESTS["executive"], persona="solopreneur")
        assert agent.name == "ExecutiveAgent"

    def test_use_manifests_flag_default(self):
        # Default value when unset -- should be "true" per agent.py.
        # This test simply documents the default contract.
        assert os.getenv("USE_MANIFESTS", "true").lower() == "true"
