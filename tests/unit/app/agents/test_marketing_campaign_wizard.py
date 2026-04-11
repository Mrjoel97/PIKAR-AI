# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Configuration tests for the CampaignAgent conversational wizard (Phase 63-03).

These tests validate the structural wiring of the campaign creation wizard:
- _CAMPAIGN_INSTRUCTION contains the 6-step wizard flow prompt
- CampaignAgent has pre-flight platform connection check tools
- CampaignAgent retains the summarize_campaign_performance follow-up tool
- MARKETING_AGENT_INSTRUCTION routing table directs wizard intents to CampaignAgent
- Tool count stays within a reasonable bound (no bloat)

The actual conversational behavior is driven by the LLM following the instruction
and is validated via eval datasets, not unit tests. These tests guard against
regressions in the wiring that would break the wizard's ability to function.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def marketing_module():
    """Load app.agents.marketing.agent once for the whole module."""
    from app.agents.marketing import agent as marketing_agent_module

    return marketing_agent_module


@pytest.fixture(scope="module")
def campaign_agent(marketing_module):
    """Return the CampaignAgent sub-agent (index 0 in the parent sub_agents list)."""
    parent = marketing_module.marketing_agent
    # CampaignAgent is always the first sub-agent per _MARKETING_SUB_AGENTS ordering
    campaign = parent.sub_agents[0]
    assert campaign.name == "CampaignAgent", (
        f"Expected first sub-agent to be CampaignAgent, got {campaign.name}"
    )
    return campaign


@pytest.fixture(scope="module")
def campaign_tool_names(campaign_agent) -> list[str]:
    """Return a list of tool names on the CampaignAgent for assertion convenience."""
    return [
        t.__name__ if hasattr(t, "__name__") else str(t)
        for t in campaign_agent.tools
    ]


class TestCampaignWizardInstruction:
    """Verify _CAMPAIGN_INSTRUCTION contains the wizard prompt fragments."""

    def test_campaign_agent_has_wizard_instruction(self, campaign_agent) -> None:
        """The wizard section and each step's core prompt must be present."""
        instruction = campaign_agent.instruction

        # Top-level section header
        assert "CAMPAIGN CREATION WIZARD" in instruction, (
            "Wizard section header missing from CampaignAgent instruction"
        )

        # Step 1: Goal elicitation
        assert "What are you promoting" in instruction, (
            "Step 1 goal question missing"
        )

        # Step 2: Audience elicitation
        assert "ideal customer" in instruction, (
            "Step 2 audience question missing"
        )

        # Step 3: Budget elicitation
        assert "daily budget" in instruction, (
            "Step 3 daily budget question missing"
        )

        # Step 4: Platform recommendation
        assert "Meta Ads" in instruction and "Google Ads" in instruction, (
            "Step 4 platform recommendation missing Google/Meta guidance"
        )

        # Step 5: Paused state + approval safety
        assert "PAUSED" in instruction, (
            "Step 5 PAUSED status safety language missing"
        )

        # Step 6: Post-creation follow-up
        assert "ad copy" in instruction, (
            "Step 6 ad copy follow-up offer missing"
        )

    def test_wizard_instruction_has_six_steps(self, campaign_agent) -> None:
        """All six wizard steps should be explicitly labeled in the instruction."""
        instruction = campaign_agent.instruction
        for step in ("Step 1", "Step 2", "Step 3", "Step 4", "Step 5", "Step 6"):
            assert step in instruction, f"Wizard {step} missing from instruction"

    def test_wizard_delegates_creation_to_ad_platform_agent(
        self, campaign_agent
    ) -> None:
        """The wizard must escalate real ad campaign creation to AdPlatformAgent."""
        instruction = campaign_agent.instruction
        assert "AdPlatformAgent" in instruction, (
            "Wizard must reference AdPlatformAgent as the delegate for real API calls"
        )
        # Must reference the actual tool functions it hands off to
        assert "create_google_ads_campaign" in instruction
        assert "create_meta_ads_campaign" in instruction


class TestCampaignAgentTooling:
    """Verify CampaignAgent has the tools required to run the wizard."""

    def test_campaign_agent_has_connection_tools(
        self, campaign_tool_names
    ) -> None:
        """Pre-flight platform connection checks must be on CampaignAgent."""
        assert "connect_google_ads_status" in campaign_tool_names, (
            f"connect_google_ads_status missing from CampaignAgent tools: "
            f"{campaign_tool_names}"
        )
        assert "connect_meta_ads_status" in campaign_tool_names, (
            f"connect_meta_ads_status missing from CampaignAgent tools: "
            f"{campaign_tool_names}"
        )

    def test_campaign_agent_has_performance_tool(
        self, campaign_tool_names
    ) -> None:
        """Post-creation follow-up requires summarize_campaign_performance."""
        assert "summarize_campaign_performance" in campaign_tool_names, (
            f"summarize_campaign_performance missing from CampaignAgent tools: "
            f"{campaign_tool_names}"
        )

    def test_campaign_agent_has_utm_tools(self, campaign_tool_names) -> None:
        """Wizard calls generate_utm_params and save_campaign_utm after creation."""
        assert "generate_utm_params" in campaign_tool_names
        assert "save_campaign_utm" in campaign_tool_names

    def test_campaign_tools_count_reasonable(self, campaign_tool_names) -> None:
        """Tool count should stay in the 12-20 range: original 12 + wizard additions."""
        count = len(campaign_tool_names)
        assert 12 <= count <= 20, (
            f"CampaignAgent tool count {count} outside expected range 12-20. "
            f"Tools: {campaign_tool_names}"
        )

    def test_campaign_tools_are_unique(self, campaign_tool_names) -> None:
        """No duplicate tool registrations after wiring in connection checks."""
        assert len(campaign_tool_names) == len(set(campaign_tool_names)), (
            f"Duplicate tools registered on CampaignAgent: {campaign_tool_names}"
        )


class TestParentRoutingForWizard:
    """Verify MARKETING_AGENT_INSTRUCTION routes wizard intents to CampaignAgent."""

    def test_parent_routing_includes_wizard(self, marketing_module) -> None:
        """Parent instruction must mention the wizard as a CampaignAgent flow."""
        parent_instruction = marketing_module.MARKETING_AGENT_INSTRUCTION
        assert "wizard" in parent_instruction.lower(), (
            "Parent MARKETING_AGENT_INSTRUCTION must reference the wizard flow"
        )
        assert "CampaignAgent" in parent_instruction, (
            "Parent must know CampaignAgent as the wizard delegate"
        )

    def test_parent_routing_mentions_campaign_intents(
        self, marketing_module
    ) -> None:
        """Parent routing table should include campaign creation intent language."""
        parent_instruction = marketing_module.MARKETING_AGENT_INSTRUCTION
        lowered = parent_instruction.lower()
        # At least one natural-language campaign creation intent should be present
        intent_phrases = [
            "launch a campaign",
            "run ads",
            "promote my product",
        ]
        matched = [phrase for phrase in intent_phrases if phrase in lowered]
        assert matched, (
            f"Parent routing table missing campaign creation intents. "
            f"Expected any of {intent_phrases} in MARKETING_AGENT_INSTRUCTION"
        )

    def test_marketing_agent_has_campaign_sub_agent(
        self, marketing_module
    ) -> None:
        """Parent marketing_agent must expose CampaignAgent as a sub-agent."""
        parent = marketing_module.marketing_agent
        sub_names = [sa.name for sa in parent.sub_agents]
        assert "CampaignAgent" in sub_names, (
            f"CampaignAgent missing from marketing_agent sub_agents: {sub_names}"
        )
