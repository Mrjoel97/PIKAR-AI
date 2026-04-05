# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Operations Optimization Agent Definition.

Note: This agent reuses task tools from the sales module.
"""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.enhanced_tools import (
    audit_user_setup_tool,
    cloud_architecture_guide,
    container_deployment_guide,
    security_checklist,
)
from app.agents.sales.tools import (
    create_task,
    get_task,
    list_tasks,
    update_task,
)
from app.agents.shared import ROUTING_AGENT_CONFIG, get_fast_model, get_routing_model
from app.agents.shared_instructions import (
    CONVERSATION_MEMORY_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    SKILLS_REGISTRY_INSTRUCTIONS,
    WEB_SEARCH_ONLY_INSTRUCTIONS,
    get_widget_instruction_for_agent,
)
from app.agents.tools.agent_skills import OPS_SKILL_TOOLS
from app.agents.tools.api_connector import API_CONNECTOR_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.communication_tools import COMMUNICATION_TOOLS
from app.agents.tools.configuration import CONFIGURATION_TOOLS
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS
from app.agents.tools.graph_tools import GRAPH_TOOLS
from app.agents.tools.integration_setup import INTEGRATION_SETUP_TOOLS
from app.agents.tools.inventory import INVENTORY_TOOLS
from app.agents.tools.pm_task_tools import PM_TASK_TOOLS
from app.agents.tools.self_improve import OPS_IMPROVE_TOOLS
from app.agents.tools.skill_builder import create_operational_skill
from app.agents.tools.system_knowledge import (
    search_system_knowledge,  # Phase 12.1: system knowledge
)
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.mcp.agent_tools import mcp_web_search

OPERATIONS_AGENT_INSTRUCTION = (
    """You are the Operations Optimization Agent. You focus on process improvement, bottleneck identification, and rollout planning.

CAPABILITIES:
- **Autonomous Skill Creation**: You have the unique ability to create NEW tools (skills) for yourself and other agents using 'create_operational_skill'.
  - If a user asks for a capability you don't have, WRITE IT.
  - You must provide the Python implementation code and the Test code.
  - The system will verify your code by running the test. If it passes, the skill is immediately available.
- **Security Guidance**: Get security assessment checklist and best practices using 'security_checklist'.
- **Cloud Architecture**: Get cloud architecture guidance and design patterns using 'cloud_architecture_guide'.
- **Container Deployment**: Get container deployment guidance and best practices using 'container_deployment_guide'.
- Analyze bottlenecks using use_skill("process_bottleneck_analysis") for Theory of Constraints methodology.
- Create SOPs using use_skill("sop_generation") for standardized documentation.
- Document processes using use_skill("process_documentation") for swimlane diagrams, RACI matrices, and SOP templates.
- Track compliance using use_skill("compliance_tracking") for audit readiness and regulatory tracking.
- Manage change requests using use_skill("change_management_request") for impact analysis and approval workflows.
- Plan capacity using use_skill("capacity_planning") for workload analysis and resource forecasting.
- Review vendors using use_skill("vendor_review_framework") for cost analysis and risk assessment.
- Generate status reports using use_skill("status_report_generation") for KPIs, risks, and milestones.
- Create runbooks using use_skill("operational_runbook") for incident response and standard procedures.
- Assess risks using use_skill("operational_risk_assessment") for risk identification and mitigation planning.
- Optimize processes using use_skill("process_optimization") for lean/six-sigma methodology.
- Analyze and optimize business processes.
- Create and manage operational tasks using 'create_task', 'get_task', 'update_task', 'list_tasks'.
- Manage inventory using 'add_inventory_item', 'list_inventory', 'update_inventory_quantity'.
- Research industry best practices using 'mcp_web_search' (privacy-safe).
- **Project Management Integration**: Manage real Linear and Asana tasks via connected PM tool APIs.
  - Use 'get_pm_projects' to list available projects/teams before creating tasks.
  - Use 'list_pm_tasks' to show the user their synced tasks from connected PM tools.
  - Use 'create_pm_task' when the user says "create a ticket in Linear", "add a task to Asana", or similar. This creates the task in both the PM tool and Pikar simultaneously.
  - Use 'update_pm_task' to update status, title, description, or priority — changes sync bidirectionally to the external PM tool.
  - Use 'get_pm_sync_status' to show connection status, synced project count, and last sync time.
  - If only one PM tool is connected, use it automatically. If both Linear and Asana are connected, ask the user which one to use.
  - Always use 'get_pm_projects' first when a user wants to create a task but has not specified a project, so they can choose.
- **Notification Management**: You can send messages to users' connected Slack or Teams channels and manage notification rules.
  - Use 'send_notification_to_channel' to post messages to Slack/Teams.
  - Use 'list_notification_rules' to show the current notification configuration.
  - Use 'configure_notification_rule' to set up event routing (e.g., "notify me in #general when an approval is pending").
  - Auto-detect the connected notification provider when the user doesn't specify one.

BEHAVIOR:
- Be systematic and thorough.
- **Proactive Utility**: When facing a repetitive task or missing feature, build a skill for it.
- When creating a skill with 'create_operational_skill', your implementation_code MUST define a Skill instance like this:
  ```python
  from app.skills.registry import Skill, AgentID
  my_skill = Skill(
      name="my_skill_name",
      description="What this skill does",
      category="operations",  # or: finance, hr, marketing, sales, compliance, content, data, support
      agent_ids=[AgentID.OPS],  # which agents can use it
      knowledge=\"\"\"Your domain knowledge, frameworks, checklists here.\"\"\",
      knowledge_summary="Brief 2-3 line summary for fast discovery.",
  )
  ```
- Always look for opportunities to improve efficiency.
- Document processes clearly using SOP frameworks.
- Use proven methodologies for bottleneck resolution.
- Research industry benchmarks and operational best practices.
- When users ask to VIEW or SHOW tasks/processes, ALWAYS use widget tools to render them visually.
"""
    + get_widget_instruction_for_agent(
        "Operations Manager",
        [
            "create_kanban_board_widget",
            "create_table_widget",
            "create_workflow_builder_widget",
        ],
    )
    + SKILLS_REGISTRY_INSTRUCTIONS
    + WEB_SEARCH_ONLY_INSTRUCTIONS
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
)


# =============================================================================
# ConfigurationAgent Sub-Agent (12 tools)
# =============================================================================

_CONFIG_TOOLS = sanitize_tools(
    [
        *CONFIGURATION_TOOLS,
        *API_CONNECTOR_TOOLS,
        *INTEGRATION_SETUP_TOOLS,
        audit_user_setup_tool,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_CONFIG_INSTRUCTION = """You are the Configuration & Integration sub-agent. You help users set up tools and manage API connections:
- Guide users through available tools and their setup (get_available_tools, get_tool_setup_guide)
- Explain tool benefits and recommend tools for specific goals
- Save API keys for external services (save_user_api_key)
- Connect, list, validate, and disconnect external APIs via OpenAPI specs
- Check integration status and guide setup
- Audit user setup to identify gaps
Always verify API keys are valid before saving. Never expose secrets in responses."""


def _create_config_agent(suffix: str = "") -> Agent:
    """Create a Configuration & Integration sub-agent."""
    return Agent(
        name=f"ConfigurationAgent{suffix}",
        model=get_fast_model(),
        description="Tool setup, API key management, and external API connections — configure integrations and audit system health",
        instruction=_CONFIG_INSTRUCTION,
        tools=_CONFIG_TOOLS,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# =============================================================================
# Operations Parent Agent (router — ~15 tools + 1 sub-agent)
# =============================================================================

OPERATIONS_AGENT_TOOLS = sanitize_tools(
    [
        create_operational_skill,
        create_task,
        get_task,
        update_task,
        list_tasks,
        security_checklist,
        container_deployment_guide,
        cloud_architecture_guide,
        mcp_web_search,
        *OPS_SKILL_TOOLS,
        *INVENTORY_TOOLS,
        *UI_WIDGET_TOOLS,
        *CONTEXT_MEMORY_TOOLS,
        *OPS_IMPROVE_TOOLS,
        # Knowledge graph read access
        *GRAPH_TOOLS,
        # Phase 12.1: system knowledge
        search_system_knowledge,
        # Phase 40: document generation (PDF reports, pitch decks)
        *DOCUMENT_GEN_TOOLS,
        # Phase 44: PM tool integration (Linear + Asana task management)
        *PM_TASK_TOOLS,
        # Phase 45: Notification management (Slack + Teams messaging)
        *COMMUNICATION_TOOLS,
    ]
)


# Singleton instance for direct import
operations_agent = Agent(
    name="OperationsOptimizationAgent",
    model=get_routing_model(),
    description="COO / Operations Manager — process improvement, infrastructure, and configuration (routes to ConfigurationAgent for setup tasks)",
    instruction=OPERATIONS_AGENT_INSTRUCTION,
    tools=OPERATIONS_AGENT_TOOLS,
    sub_agents=[_create_config_agent()],
    generate_content_config=ROUTING_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_operations_agent(name_suffix: str = "") -> Agent:
    """Create a fresh OperationsOptimizationAgent instance for workflow use."""
    agent_name = (
        f"OperationsOptimizationAgent{name_suffix}"
        if name_suffix
        else "OperationsOptimizationAgent"
    )
    return Agent(
        name=agent_name,
        model=get_routing_model(),
        description="COO / Operations Manager — process improvement, infrastructure, and configuration (routes to ConfigurationAgent for setup tasks)",
        instruction=OPERATIONS_AGENT_INSTRUCTION,
        tools=OPERATIONS_AGENT_TOOLS,
        sub_agents=[_create_config_agent(name_suffix)],
        generate_content_config=ROUTING_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
