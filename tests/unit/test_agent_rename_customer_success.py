# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Rename consistency tests for the Customer Success Manager agent.

Verifies that the Customer Support Agent has been correctly renamed to
"Customer Success Manager" across all backend files: agent description,
instruction string, factory function, department routing display name,
and skills registry mapping.
"""

from unittest.mock import MagicMock, patch


class TestAgentDescriptionContainsCustomerSuccess:
    """Test that the singleton agent description reflects the new name."""

    def test_agent_description_contains_customer_success(self) -> None:
        """Agent description must say 'Customer Success Manager', not 'CTO'."""
        from app.agents.customer_support import customer_support_agent

        assert "Customer Success Manager" in customer_support_agent.description, (
            f"Expected 'Customer Success Manager' in description, got: {customer_support_agent.description!r}"
        )
        assert "CTO" not in customer_support_agent.description, (
            f"Old 'CTO' label must be removed from description, got: {customer_support_agent.description!r}"
        )


class TestAgentInstructionContainsCustomerSuccess:
    """Test that the instruction constant reflects the new positioning."""

    def test_agent_instruction_contains_customer_success(self) -> None:
        """CUSTOMER_SUPPORT_AGENT_INSTRUCTION must open with 'Customer Success Manager'."""
        from app.agents.customer_support.agent import CUSTOMER_SUPPORT_AGENT_INSTRUCTION

        assert "Customer Success Manager" in CUSTOMER_SUPPORT_AGENT_INSTRUCTION, (
            "Expected 'Customer Success Manager' in CUSTOMER_SUPPORT_AGENT_INSTRUCTION"
        )
        assert "CTO" not in CUSTOMER_SUPPORT_AGENT_INSTRUCTION, (
            "Old 'CTO' label must not appear in CUSTOMER_SUPPORT_AGENT_INSTRUCTION"
        )


class TestFactoryDescriptionMatchesSingleton:
    """Test that factory-created instances use the same description as the singleton."""

    def test_factory_description_matches_singleton(self) -> None:
        """create_customer_support_agent() description must equal singleton description."""
        from app.agents.customer_support import (
            create_customer_support_agent,
            customer_support_agent,
        )

        factory_agent = create_customer_support_agent()
        assert factory_agent.description == customer_support_agent.description, (
            f"Factory description {factory_agent.description!r} does not match "
            f"singleton description {customer_support_agent.description!r}"
        )


class TestDepartmentRoutingDisplayName:
    """Test that the SUPPORT route display name uses the new label."""

    def test_department_routing_display_name(self) -> None:
        """SUPPORT route display_name must be 'Customer Success', not 'Customer Support'."""
        from app.config.department_routing import DEPARTMENT_ROUTING

        support_route = DEPARTMENT_ROUTING["SUPPORT"]
        assert support_route.display_name == "Customer Success", (
            f"Expected display_name 'Customer Success', got: {support_route.display_name!r}"
        )


class TestSkillsRegistryCommentUpdated:
    """Test that the skills registry SUPP entry still maps to the correct agent name."""

    def test_skills_registry_comment_updated(self) -> None:
        """AgentID.SUPP must map to 'CustomerSupportAgent' in AGENT_ID_TO_NAME."""
        from app.skills.registry import AGENT_ID_TO_NAME, AgentID

        assert AGENT_ID_TO_NAME[AgentID.SUPP] == "CustomerSupportAgent", (
            f"Expected AGENT_ID_TO_NAME[AgentID.SUPP] == 'CustomerSupportAgent', "
            f"got: {AGENT_ID_TO_NAME[AgentID.SUPP]!r}"
        )
