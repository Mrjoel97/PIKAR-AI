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

"""Pikar AI Executive Agent - Central Orchestrator for Business Operations.

This module implements the Executive Agent, which serves as the primary
interface for users and orchestrates tasks across specialized agents.
"""

import logging
import uuid
from pathlib import Path

# Production App configuration imports
from google.adk.apps import App
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps.app import EventsCompactionConfig

from app.agents.base_agent import PikarAgent as Agent
from app.agents.shared import get_fallback_model, get_model, get_routing_model, ROUTING_AGENT_CONFIG

# Import shared instruction blocks for consistent behavior across agents
from app.agents.shared_instructions import (
    SKILLS_REGISTRY_INSTRUCTIONS,
    CONVERSATION_MEMORY_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    get_error_and_escalation_instructions,
)

# Import context memory tools and callbacks for conversation continuity
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)

# Import specialized agents for sub_agents hierarchy
from app.agents.specialized_agents import SPECIALIZED_AGENTS

# Import Skill tools for accessing and creating skills (agent-aware)
from app.agents.tools.agent_skills import EXEC_SKILL_TOOLS
from app.agents.tools.calendar_tool import CALENDAR_TOOLS

# Import Configuration tools for helping users set up MCP tools
from app.agents.tools.configuration import CONFIGURATION_TOOLS

# Import Deep Research tools for intelligent research behavior
from app.agents.tools.deep_research import DEEP_RESEARCH_TOOLS
from app.agents.enhanced_tools import audit_user_setup_tool

# Import Self-Improvement tools for autonomous skill iteration
from app.agents.tools.self_improve import EXEC_IMPROVE_TOOLS

# Import Google Workspace tools for document creation
from app.agents.tools.docs import DOCS_TOOLS
from app.agents.tools.forms import FORMS_TOOLS
from app.agents.tools.gmail import GMAIL_TOOLS
from app.agents.tools.google_sheets import GOOGLE_SHEETS_TOOLS
from app.agents.tools.media import (
    MEDIA_TOOLS,  # Add native media tools including create_pro_video
)
from app.agents.tools.brain_dump import get_braindump_document

# Import notification tools
from app.agents.tools.notifications import NOTIFICATION_TOOLS

# Import briefing tools for daily email triage
from app.agents.tools.briefing_tools import BRIEFING_TOOLS

# Import magic link approval tools for email-based approve/reject flows
from app.agents.tools.magic_link_approvals import MAGIC_LINK_TOOLS

# Import UI widget tools for agent-to-UI feature
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS

# Import workflow tools
from app.agents.tools.workflows import WORKFLOW_TOOLS
from app.agents.tools.integration_setup import INTEGRATION_SETUP_TOOLS
from app.mcp.tools.canva_media import CANVA_TOOLS

# Import MCP tools for payments, media, and landing pages
from app.mcp.tools.stripe_payments import STRIPE_TOOLS
from app.mcp.tools.supabase_landing import SUPABASE_LANDING_TOOLS

# Import knowledge injection tools
from app.orchestration.knowledge_tools import KNOWLEDGE_INJECTION_TOOLS

import os
_ENABLE_CONTEXT_CACHE = os.getenv("ENABLE_CONTEXT_CACHE", "true").lower() == "true"

logger = logging.getLogger(__name__)

# Telemetry / Journey Discovery

# from google.adk.events import ToolCallEvent, ToolOutputEvent
# from google.adk.runtime import InvocationContext

# Configure Vertex AI
# os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "my-project-pk-484623")
# os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
# os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


# =============================================================================
# Global Business Tools
# =============================================================================

def get_revenue_stats() -> dict:
    """Provides current revenue statistics and financial health metrics.

    Returns:
        Dictionary containing revenue data, trends, and financial KPIs.
    """
    # In production, this would query the database
    return {
        "revenue": 1000.0,
        "currency": "USD",
        "period": "current_month",
        "trend": "stable"
    }


def search_business_knowledge(query: str) -> dict:
    """Search the Knowledge Vault for relevant business information.

    This tool queries the RAG system to find context and information
    about the business, products, customers, and historical decisions.

    Args:
        query: The search query to find relevant business knowledge.

    Returns:
        Dictionary containing search results with relevant context.
    """
    try:
        from app.rag.knowledge_vault import search_knowledge
        return search_knowledge(query, top_k=5)
    except Exception:
        # Fallback for when Knowledge Vault is not configured
        return {"results": [], "query": query, "note": "Knowledge Vault not configured"}


def update_initiative_status(initiative_id: str, status: str) -> dict:
    """Updates the status of a business initiative or project.

    Args:
        initiative_id: The unique identifier of the initiative.
        status: The new status (e.g., 'in_progress', 'completed', 'blocked').

    Returns:
        Dictionary confirming the update.
    """
    logger.info(f"Updating initiative {initiative_id} to {status}")
    return {"success": True, "initiative_id": initiative_id, "new_status": status}


def create_task(description: str, assignee: str, priority: str) -> dict:
    """Creates a new task in the task management system.

    Args:
        description: Clear description of what needs to be done.
        assignee: Who should work on this task (use 'unassigned' if no specific person).
        priority: Task priority - must be one of: low, medium, high, urgent.

    Returns:
        Dictionary with the created task details including task_id, description,
        assignee, priority, and status.
    """
    task_id = str(uuid.uuid4())
    logger.info(f"Created task '{description}' with id {task_id}")
    return {
        "task_id": task_id,
        "description": description,
        "assignee": assignee,
        "priority": priority,
        "status": "created"
    }


# NOTE: Orchestration tools removed - ADK handles delegation natively via sub_agents


# =============================================================================
# Executive Agent Definition
# =============================================================================

# Load executive instruction from external template file for easier maintenance
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_EXECUTIVE_INSTRUCTION_PATH = _PROMPTS_DIR / "executive_instruction.txt"

if _EXECUTIVE_INSTRUCTION_PATH.exists():
    _EXEC_BASE = _EXECUTIVE_INSTRUCTION_PATH.read_text(encoding="utf-8")
else:
    # Fallback inline instruction if template file is missing
    logger.warning("Executive instruction template not found at %s, using minimal fallback", _EXECUTIVE_INSTRUCTION_PATH)
    _EXEC_BASE = """You are the Executive Agent for Pikar AI - the Chief of Staff and Central Orchestrator.
You are the primary interface between the user and Pikar AI's multi-agent ecosystem.
Coordinate specialized agents to accomplish complex tasks. Use available tools to help users.
"""

# Compose final instruction from base template + shared instruction blocks
# This keeps the exec agent in sync with updates to shared blocks used by all agents
EXECUTIVE_INSTRUCTION = _EXEC_BASE + SKILLS_REGISTRY_INSTRUCTIONS + CONVERSATION_MEMORY_INSTRUCTIONS + SELF_IMPROVEMENT_INSTRUCTIONS + get_error_and_escalation_instructions(
    "Executive Agent",
    """- Escalate to the user when a delegated specialist agent returns an error or unexpected result
- Escalate to the user when a task requires cross-domain coordination that affects budget, legal standing, or public reputation
- If multiple specialist agents return conflicting recommendations, synthesize and present the trade-offs rather than picking one silently
- Never auto-approve workflows that involve financial transactions, public communications, or hiring decisions
- If a specialist agent is unavailable (model error, timeout), inform the user and suggest an alternative approach"""
)

from app.agents.tools.base import sanitize_tools as _sanitize

_EXECUTIVE_TOOLS = _sanitize([
    get_revenue_stats,
    search_business_knowledge,
    get_braindump_document,
    update_initiative_status,
    create_task,
    audit_user_setup_tool,
    *KNOWLEDGE_INJECTION_TOOLS,
    *NOTIFICATION_TOOLS,
    *WORKFLOW_TOOLS,
    *INTEGRATION_SETUP_TOOLS,
    *UI_WIDGET_TOOLS,
    *EXEC_SKILL_TOOLS,
    *CONFIGURATION_TOOLS,
    *CONTEXT_MEMORY_TOOLS,
    *CALENDAR_TOOLS,
    *DEEP_RESEARCH_TOOLS,
    *DOCS_TOOLS,
    *FORMS_TOOLS,
    *GMAIL_TOOLS,
    *GOOGLE_SHEETS_TOOLS,
    *MEDIA_TOOLS,
    *CANVA_TOOLS,
    *STRIPE_TOOLS,
    *SUPABASE_LANDING_TOOLS,
    *EXEC_IMPROVE_TOOLS,
    *BRIEFING_TOOLS,
    *MAGIC_LINK_TOOLS,
])

def _build_executive_agent(model, sub_agents=None):
    """Build the Executive Agent with the given model and sub-agents list."""
    return Agent(
        name="ExecutiveAgent",
        model=model,
        description="Chief of Staff / Central Orchestrator - Primary interface for Pikar AI users",
        instruction=EXECUTIVE_INSTRUCTION,
        tools=_EXECUTIVE_TOOLS,
        sub_agents=sub_agents if sub_agents is not None else [],
        generate_content_config=ROUTING_AGENT_CONFIG,
        # Context memory callbacks for persistent user fact storage
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def _build_fallback_sub_agents():
    """Create fresh sub-agent instances for the fallback agent.
    
    ADK enforces that each agent instance can only have one parent.
    The primary agent already "owns" the singleton sub-agents, so the fallback
    must create new instances via factory functions to avoid the
    'already has parent' validation error.
    """
    from app.agents.specialized_agents import (
        create_financial_agent, create_content_agent, create_strategic_agent,
        create_sales_agent, create_marketing_agent, create_operations_agent,
        create_hr_agent, create_compliance_agent, create_customer_support_agent,
        create_data_agent,
    )
    return [
        create_financial_agent("_fb"), create_content_agent("_fb"),
        create_strategic_agent("_fb"), create_sales_agent("_fb"),
        create_marketing_agent("_fb"), create_operations_agent("_fb"),
        create_hr_agent("_fb"), create_compliance_agent("_fb"),
        create_customer_support_agent("_fb"), create_data_agent("_fb"),
    ]


# Primary agent with full sub-agent delegation
executive_agent = _build_executive_agent(get_routing_model(), sub_agents=SPECIALIZED_AGENTS)
# Fallback agent with FRESH sub-agent instances (avoids ADK 'already has parent' error)
executive_agent_fallback = _build_executive_agent(
    get_fallback_model(), sub_agents=_build_fallback_sub_agents()
)

# Create the production application with ADK best practices
app = App(
    root_agent=executive_agent,
    name="agents",  # Must match directory where agent is loaded from (app/agents/)
    # Context cache enabled
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,    # Minimum tokens before caching kicks in
        ttl_seconds=600     # Cache TTL: 10 minutes
    ) if _ENABLE_CONTEXT_CACHE else None,
    # Manage long conversation history automatically
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=80,  # High interval to prevent premature context loss
        overlap_size=30          # Keep 30 events overlap for rich conversation context
    ),
)

# Fallback app used when primary model is unavailable (run_sse retry)
app_fallback = App(
    root_agent=executive_agent_fallback,
    name="agents",
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=80,
        overlap_size=30,
    ),
)
