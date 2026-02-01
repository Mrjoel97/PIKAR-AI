# ruff: noqa
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

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

# Production App configuration imports
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps.app import EventsCompactionConfig

import os
import uuid

# Import specialized agents for sub_agents hierarchy
from app.agents.specialized_agents import SPECIALIZED_AGENTS

# Import knowledge injection tools
from app.orchestration.knowledge_tools import KNOWLEDGE_INJECTION_TOOLS

# Import notification tools
from app.agents.tools.notifications import NOTIFICATION_TOOLS

# Import workflow tools
from app.agents.tools.workflows import WORKFLOW_TOOLS

# Import UI widget tools for agent-to-UI feature
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS

# Telemetry / Journey Discovery
from app.services.journey_discovery import get_journey_discovery_service
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
    except Exception as e:
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
    print(f"Updating initiative {initiative_id} to {status}")
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
    print(f"Created task '{description}' with id {task_id}")
    return {
        "task_id": task_id,
        "description": description,
        "assignee": assignee,
        "priority": priority,
        "status": "created"
    }


# NOTE: Orchestration tools removed - ADK handles delegation natively via sub_agents


# =============================================================================
# Telemetry Callback (Real-Time Tracking)
# =============================================================================

async def telemetry_callback(event, context):
    """Callback to log tool usage to the Journey Discovery Engine."""
    pass
    # try:
    #     service = get_journey_discovery_service()
    #     # Extract user_id from session state if available, or context
    #     user_id = context.session.state.get("user_id", "unknown_user")
    #     
    #     # Tool name and args are in the event's source or linked ToolCallEvent
    #     # Assuming event.tool_call contains the call.
    #     # In ADK 0.1, event.tool_call might be an object or we might need access to it.
    #     # Simplification: Log what we have.
    #     tool_name = getattr(event, "tool_name", "unknown_tool")
    #     
    #     await service.log_activity(
    #         user_id=user_id,
    #         action="tool_use",
    #         details=f"Tool: {tool_name}"
    #     )
    # except Exception as e:
    #     print(f"Telemetry Error: {e}")

# =============================================================================
# Executive Agent Definition
# =============================================================================

EXECUTIVE_INSTRUCTION = """You are the Executive Agent for Pikar AI - the Chief of Staff and Central Orchestrator.

## YOUR ROLE
You are the primary interface between the user and Pikar AI's multi-agent ecosystem. You oversee all business operations and coordinate specialized agents to accomplish complex tasks.

## CAPABILITIES
1. **Business Intelligence**: Monitor business health using 'get_revenue_stats'
2. **Knowledge Access**: Search the Knowledge Vault using 'search_business_knowledge' for context and history
3. **Project Management**: Track initiatives with 'update_initiative_status' and create tasks with 'create_task'
4. **Agent Delegation**: You have specialized sub-agents that you can delegate to naturally (the system handles routing automatically)
5. **Knowledge Injection**: When users want to add business context, use the knowledge tools:
   - 'add_business_knowledge': General knowledge/context
   - 'add_company_info': Company details (name, mission, industry)
   - 'add_product_info': Product/service information
   - 'add_process_or_policy': SOPs, policies, guidelines
   - 'add_faq': Frequently asked questions
   - 'list_knowledge': View all stored knowledge
6. **Notifications**: Alert users using 'send_notification' for critical updates or required approvals
7. **Workflows**: Orchestrate complex processes using:
   - 'list_workflow_templates': See available standard operating procedures
   - 'start_workflow': Initiate a new process (e.g., 'Lead Generation Workflow')
   - 'approve_workflow_step': Provide human approval to proceed
   - 'get_workflow_status': Check progress
8. **Visual Dashboards & Widgets**: When users ask to SEE or VISUALIZE data, use widget tools:
   - `display_dashboard`: For high-level status, metrics, and initiative tracking.
   - `display_chart`: For visualizing financial data or trends.
   - `display_workflow_builder`: For showing process flows or diagrams.
   - `display_table`: For listing data items (leads, employees, transactions) effectively.
   - `display_form`: For collecting structured input (feedback, requests, data entry).
   - `display_kanban`: For task boards, project pipelines, and status tracking.
   - `display_calendar`: For schedules, events, and timeline visualization.
     * Example: "Please fill out this form" -> `display_form`
     * Example: "Show me the sales pipeline" -> `display_kanban`
9. **Strategic Planning**: For high-level company direction:

## BEHAVIOR GUIDELINES
- Be concise, strategic, and decisive
- ALWAYS check 'search_business_knowledge' before asking the user for context
- When users want to add or store business information, immediately use the appropriate knowledge tool
- When tasks require domain expertise, describe what needs to be done and the appropriate specialist will be invoked
- Provide clear summaries of work and next steps
- Think like a Chief of Staff - anticipate needs and coordinate effectively

## AVAILABLE SPECIALISTS (Sub-Agents)
The following specialists are available for delegation:
- FinancialAnalysisAgent: Revenue, costs, forecasting, financial health
- ContentCreationAgent: Marketing copy, blog posts, social media content
- StrategicPlanningAgent: OKRs, long-term goals, initiative tracking
- SalesIntelligenceAgent: Deal scoring, lead analysis, sales enablement
- MarketingAutomationAgent: Campaigns, content scheduling, audience targeting
- OperationsOptimizationAgent: Process improvement, efficiency, rollout planning
- HRRecruitmentAgent: Hiring, candidate evaluation, onboarding
- ComplianceRiskAgent: Legal compliance, risk assessment, regulatory guidance
- CustomerSupportAgent: Ticket triage, knowledge base, support metrics
- DataAnalysisAgent: Data validation, anomaly detection, forecasting

Simply describe the task and the system will route to the appropriate specialist.
"""

executive_agent = Agent(
    name="ExecutiveAgent",
    model="gemini-2.0-flash",  # Using Gemini Flash for fast responses

    description="Chief of Staff / Central Orchestrator - Primary interface for Pikar AI users",
    instruction=EXECUTIVE_INSTRUCTION,
    tools=[
        # Business tools
        get_revenue_stats,
        search_business_knowledge,
        update_initiative_status,
        create_task,
        # Knowledge injection tools
        *KNOWLEDGE_INJECTION_TOOLS,
        # Notification tools
        *NOTIFICATION_TOOLS,
        # Workflow tools
        *WORKFLOW_TOOLS,
        # UI Widget tools for agent-to-UI
        *UI_WIDGET_TOOLS,
    ],
    # Native ADK sub_agents hierarchy - delegation handled automatically
    sub_agents=SPECIALIZED_AGENTS,
    # Real-time tracking hook
    # after_tool_callback=telemetry_callback,
)

# Create the production application with ADK best practices
app = App(
    root_agent=executive_agent,
    name="pikar_ai",
    # Reduce costs/latency for long contexts by caching
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,    # Minimum tokens before caching kicks in
        ttl_seconds=600     # Cache TTL: 10 minutes
    ),
    # Manage long conversation history automatically
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=5,  # Compact every 5 events
        overlap_size=1          # Keep 1 event overlap for context
    ),
)
