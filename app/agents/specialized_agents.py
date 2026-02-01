# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Specialized Agents - Re-export Layer for Backward Compatibility.

This module re-exports all specialized agents from their individual modules
to maintain backward compatibility with existing imports.

For new code, prefer importing from individual modules:
    from app.agents.financial import financial_agent, create_financial_agent

This file re-exports from:
    - app.agents.financial
    - app.agents.content
    - app.agents.strategic
    - app.agents.sales
    - app.agents.marketing
    - app.agents.operations
    - app.agents.hr
    - app.agents.compliance
    - app.agents.customer_support
    - app.agents.data
"""

# Re-export shared utility (for backward compatibility)
from app.agents.shared import get_model

# Financial Agent
from app.agents.financial import financial_agent, create_financial_agent

# Content Agent
from app.agents.content import content_agent, create_content_agent

# Strategic Agent
from app.agents.strategic import strategic_agent, create_strategic_agent

# Sales Agent
from app.agents.sales import sales_agent, create_sales_agent

# Marketing Agent
from app.agents.marketing import marketing_agent, create_marketing_agent

# Operations Agent
from app.agents.operations import operations_agent, create_operations_agent

# HR Agent
from app.agents.hr import hr_agent, create_hr_agent

# Compliance Agent
from app.agents.compliance import compliance_agent, create_compliance_agent

# Customer Support Agent
from app.agents.customer_support import customer_support_agent, create_customer_support_agent

# Data Agent
from app.agents.data import data_agent, create_data_agent


# =============================================================================
# Export all specialized agents
# =============================================================================

SPECIALIZED_AGENTS = [
    financial_agent,
    content_agent,
    strategic_agent,
    sales_agent,
    marketing_agent,
    operations_agent,
    hr_agent,
    compliance_agent,
    customer_support_agent,
    data_agent,
]

__all__ = [
    # Utility
    "get_model",
    # Singleton agents (for ExecutiveAgent delegation)
    "financial_agent",
    "content_agent",
    "strategic_agent",
    "sales_agent",
    "marketing_agent",
    "operations_agent",
    "hr_agent",
    "compliance_agent",
    "customer_support_agent",
    "data_agent",
    "SPECIALIZED_AGENTS",
    # Factory functions (for workflow pipelines)
    "create_financial_agent",
    "create_content_agent",
    "create_strategic_agent",
    "create_sales_agent",
    "create_marketing_agent",
    "create_operations_agent",
    "create_hr_agent",
    "create_compliance_agent",
    "create_customer_support_agent",
    "create_data_agent",
]
