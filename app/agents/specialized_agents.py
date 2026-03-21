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
    - app.agents.research
"""

# Re-export shared utility (for backward compatibility)
# Compliance Agent
from app.agents.compliance import compliance_agent, create_compliance_agent

# Content Agent
from app.agents.content import content_agent, create_content_agent

# Customer Support Agent
from app.agents.customer_support import (
    create_customer_support_agent,
    customer_support_agent,
)

# Data Agent
from app.agents.data import create_data_agent, data_agent

# Financial Agent
from app.agents.financial import create_financial_agent, financial_agent

# HR Agent
from app.agents.hr import create_hr_agent, hr_agent

# Marketing Agent
from app.agents.marketing import create_marketing_agent, marketing_agent

# Operations Agent
from app.agents.operations import create_operations_agent, operations_agent

# Research Agent
from app.agents.research.agent import create_research_agent, research_agent

# Sales Agent
from app.agents.sales import create_sales_agent, sales_agent
from app.agents.shared import get_model

# Strategic Agent
from app.agents.strategic import create_strategic_agent, strategic_agent

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
    research_agent,
]

__all__ = [
    "SPECIALIZED_AGENTS",
    "compliance_agent",
    "content_agent",
    "create_compliance_agent",
    "create_content_agent",
    "create_customer_support_agent",
    "create_data_agent",
    "create_financial_agent",
    "create_hr_agent",
    "create_marketing_agent",
    "create_operations_agent",
    "create_research_agent",
    "create_sales_agent",
    "create_strategic_agent",
    "customer_support_agent",
    "data_agent",
    "financial_agent",
    "get_model",
    "hr_agent",
    "marketing_agent",
    "operations_agent",
    "research_agent",
    "sales_agent",
    "strategic_agent",
]
