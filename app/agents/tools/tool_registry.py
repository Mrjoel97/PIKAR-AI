# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Centralized Tool Registry - Maps tools to agents for automatic assignment.

This module provides a centralized registry for managing which tools are
available to which agents. It enables:
1. Automatic tool discovery based on agent ID
2. Consistent tool assignment across the codebase
3. Easy addition of new tools without modifying individual agents
"""

from typing import Callable, List, Dict
from app.skills.registry import AgentID
from app.agents.tools.base import sanitize_tools

# Lazy import to avoid circular dependencies
_tools_cache: Dict[str, List[Callable]] = {}


def _get_skill_tools_for_agent(agent_id: AgentID) -> List[Callable]:
    """Get skill tools configured for a specific agent."""
    from app.agents.tools.agent_skills import get_agent_skill_tools
    return get_agent_skill_tools(agent_id)


def _get_shared_tools() -> List[Callable]:
    """Get tools shared across all agents."""
    from app.mcp.agent_tools import mcp_web_search
    return [mcp_web_search]


def _get_domain_tools(agent_id: AgentID) -> List[Callable]:
    """Get domain-specific tools for an agent."""
    tools = []
    
    if agent_id == AgentID.FIN:
        from app.agents.financial.tools import get_revenue_stats
        from app.agents.tools.invoicing import INVOICE_TOOLS
        tools = [get_revenue_stats, *INVOICE_TOOLS]
    
    elif agent_id == AgentID.CONT:
        from app.agents.content.tools import (
            search_knowledge, save_content, get_content, 
            update_content, list_content
        )
        from app.agents.enhanced_tools import (
            generate_image, generate_short_video, generate_remotion_video,
            generate_react_component, build_portfolio,
        )
        from app.mcp.agent_tools import mcp_web_scrape, mcp_generate_landing_page
        tools = [
            search_knowledge, save_content, get_content, update_content, list_content,
            generate_image, generate_short_video, generate_remotion_video,
            generate_react_component, build_portfolio,
            mcp_web_scrape, mcp_generate_landing_page,
        ]
    
    elif agent_id == AgentID.STRAT:
        from app.agents.strategic.tools import (
            create_initiative, get_initiative, update_initiative, list_initiatives
        )
        from app.agents.enhanced_tools import generate_product_roadmap
        from app.mcp.agent_tools import mcp_web_scrape
        from app.agents.tools.adaptive_workflows import ADAPTIVE_TOOLS
        tools = [
            create_initiative, get_initiative, update_initiative, list_initiatives,
            generate_product_roadmap, mcp_web_scrape, *ADAPTIVE_TOOLS,
        ]
    
    elif agent_id == AgentID.SALES:
        from app.agents.sales.tools import create_task, get_task, update_task, list_tasks
        from app.agents.enhanced_tools import manage_hubspot
        from app.mcp.agent_tools import mcp_web_scrape
        tools = [
            create_task, get_task, update_task, list_tasks,
            manage_hubspot, mcp_web_scrape,
        ]
    
    elif agent_id == AgentID.MKT:
        from app.agents.content.tools import search_knowledge
        from app.agents.marketing.tools import (
            create_campaign, get_campaign, update_campaign, 
            list_campaigns, record_campaign_metrics
        )
        from app.agents.enhanced_tools import perform_seo_audit
        from app.mcp.agent_tools import mcp_web_scrape, mcp_generate_landing_page
        from app.agents.tools.social import SOCIAL_TOOLS
        tools = [
            search_knowledge,
            create_campaign, get_campaign, update_campaign, list_campaigns, record_campaign_metrics,
            perform_seo_audit,
            mcp_web_scrape, mcp_generate_landing_page, *SOCIAL_TOOLS,
        ]
    
    elif agent_id == AgentID.OPS:
        from app.agents.tools.skill_builder import create_operational_skill
        from app.agents.sales.tools import create_task, get_task, update_task, list_tasks
        from app.agents.enhanced_tools import (
            run_security_audit, deploy_container, architect_cloud_solution,
        )
        from app.agents.tools.inventory import INVENTORY_TOOLS
        tools = [
            create_operational_skill,
            create_task, get_task, update_task, list_tasks,
            run_security_audit, deploy_container, architect_cloud_solution,
            *INVENTORY_TOOLS,
        ]
    
    elif agent_id == AgentID.HR:
        from app.agents.content.tools import search_knowledge
        from app.agents.hr.tools import (
            create_job, get_job, update_job, list_jobs,
            add_candidate, update_candidate_status, list_candidates
        )
        tools = [
            search_knowledge,
            create_job, get_job, update_job, list_jobs,
            add_candidate, update_candidate_status, list_candidates,
        ]
    
    elif agent_id == AgentID.LEGAL:
        from app.agents.content.tools import search_knowledge
        from app.agents.compliance.tools import (
            create_audit, get_audit, update_audit, list_audits,
            create_risk, get_risk, update_risk, list_risks,
        )
        from app.mcp.agent_tools import mcp_web_scrape
        tools = [
            search_knowledge,
            create_audit, get_audit, update_audit, list_audits,
            create_risk, get_risk, update_risk, list_risks,
            mcp_web_scrape,
        ]
    
    elif agent_id == AgentID.SUPP:
        from app.agents.content.tools import search_knowledge
        from app.agents.customer_support.tools import (
            create_ticket, get_ticket, update_ticket, list_tickets
        )
        tools = [
            search_knowledge,
            create_ticket, get_ticket, update_ticket, list_tickets,
        ]
    
    elif agent_id == AgentID.DATA:
        from app.agents.content.tools import search_knowledge
        from app.agents.financial.tools import get_revenue_stats
        from app.agents.data.tools import track_event, query_events, create_report, list_reports
        from app.agents.enhanced_tools import design_rag_pipeline
        from app.mcp.agent_tools import mcp_web_scrape
        tools = [
            get_revenue_stats, search_knowledge,
            track_event, query_events, create_report, list_reports,
            design_rag_pipeline,
            mcp_web_scrape,
        ]
    
    return tools


def get_tools_for_agent(agent_id: AgentID) -> List[Callable]:
    """Get all tools available to a specific agent.
    
    This function assembles the complete tool list for an agent including:
    1. Domain-specific tools
    2. Agent-aware skill tools
    3. Shared tools (web search, etc.)
    
    Args:
        agent_id: The AgentID enum value identifying the agent.
        
    Returns:
        List of callable tools available to the agent.
    """
    # Check cache first
    cache_key = agent_id.value
    if cache_key in _tools_cache:
        return _tools_cache[cache_key]
    
    # Assemble tools
    tools = []
    
    # Add domain-specific tools
    tools.extend(_get_domain_tools(agent_id))
    
    # Add agent-aware skill tools
    tools.extend(_get_skill_tools_for_agent(agent_id))
    
    # Add shared tools
    tools.extend(_get_shared_tools())

    # Sanitize all tools: convert Dict params → str for Gemini compatibility
    tools = sanitize_tools(tools)

    # Cache for performance
    _tools_cache[cache_key] = tools

    return tools


def clear_cache() -> None:
    """Clear the tools cache. Useful for testing."""
    global _tools_cache
    _tools_cache = {}


# Agent ID to human-readable name mapping for instructions
AGENT_ROLE_DESCRIPTIONS = {
    AgentID.EXEC: "Executive Agent - Chief of Staff / Central Orchestrator",
    AgentID.FIN: "Financial Analysis Agent - CFO / Financial Analyst",
    AgentID.CONT: "Content Creation Agent - CMO / Creative Director",
    AgentID.STRAT: "Strategic Planning Agent - Chief Strategy Officer",
    AgentID.SALES: "Sales Intelligence Agent - Head of Sales",
    AgentID.MKT: "Marketing Automation Agent - Marketing Director",
    AgentID.OPS: "Operations Optimization Agent - COO / Operations Manager",
    AgentID.HR: "HR & Recruitment Agent - Human Resources Manager",
    AgentID.LEGAL: "Compliance & Risk Agent - Legal Counsel",
    AgentID.SUPP: "Customer Support Agent - CTO / IT Support",
    AgentID.DATA: "Data Analysis Agent - Data Analyst",
}
