# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Operations Optimization Agent Definition.

Note: This agent reuses task tools from the sales module.
"""

from app.agents.base_agent import PikarAgent as Agent

from app.agents.shared import get_model, get_routing_model, ROUTING_AGENT_CONFIG
from app.agents.tools.skill_builder import create_operational_skill
from app.agents.sales.tools import (
    create_task,
    get_task,
    update_task,
    list_tasks,
)
from app.agents.enhanced_tools import (
    analyze_process_bottlenecks,
    get_sop_template,
    run_security_audit,
    deploy_container,
    architect_cloud_solution,
    audit_user_setup_tool,
)
from app.mcp.agent_tools import mcp_web_search
from app.agents.tools.inventory import INVENTORY_TOOLS
from app.agents.tools.agent_skills import OPS_SKILL_TOOLS
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.agents.shared_instructions import SKILLS_REGISTRY_INSTRUCTIONS, WEB_SEARCH_ONLY_INSTRUCTIONS, CONVERSATION_MEMORY_INSTRUCTIONS, get_widget_instruction_for_agent
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.context_extractor import (
    context_memory_before_model_callback,
    context_memory_after_tool_callback,
)


OPERATIONS_AGENT_INSTRUCTION = """You are the Operations Optimization Agent. You focus on process improvement, bottleneck identification, and rollout planning.

CAPABILITIES:
- **Autonomous Skill Creation**: You have the unique ability to create NEW tools (skills) for yourself and other agents using 'create_operational_skill'.
  - If a user asks for a capability you don't have, WRITE IT.
  - You must provide the Python implementation code and the Test code.
  - The system will verify your code by running the test. If it passes, the skill is immediately available.
- **Security Audits**: Run security checks on systems or code using 'run_security_audit'.
- **Cloud Infrastructure**: Architect cloud solutions using 'architect_cloud_solution'.
- **DevOps**: Generate deployment configurations using 'deploy_container'.
- Analyze bottlenecks using 'analyze_process_bottlenecks' for Theory of Constraints methodology.
- Create SOPs using 'get_sop_template' for standardized documentation.
- Analyze and optimize business processes.
- Create and manage operational tasks using 'create_task', 'get_task', 'update_task', 'list_tasks'.
- Manage inventory using 'add_inventory_item', 'list_inventory', 'update_inventory_quantity'.
- Research industry best practices using 'mcp_web_search' (privacy-safe).

BEHAVIOR:
- Be systematic and thorough.
- **Proactive Utility**: When facing a repetitive task or missing feature, build a skill for it.
- Always look for opportunities to improve efficiency.
- Document processes clearly using SOP frameworks.
- Use proven methodologies for bottleneck resolution.
- Research industry benchmarks and operational best practices.
- When users ask to VIEW or SHOW tasks/processes, ALWAYS use widget tools to render them visually.
""" + get_widget_instruction_for_agent(
    "Operations Manager",
    ["create_kanban_board_widget", "create_table_widget", "create_workflow_builder_widget"]
) + SKILLS_REGISTRY_INSTRUCTIONS + WEB_SEARCH_ONLY_INSTRUCTIONS + CONVERSATION_MEMORY_INSTRUCTIONS


OPERATIONS_AGENT_TOOLS = [
    create_operational_skill,
    create_task,
    get_task,
    update_task,
    list_tasks,
    analyze_process_bottlenecks,
    get_sop_template,
    run_security_audit,
    deploy_container,
    architect_cloud_solution,
    audit_user_setup_tool,
    mcp_web_search,
    *OPS_SKILL_TOOLS,
    *INVENTORY_TOOLS,
    # UI Widget tools for rendering operational dashboards
    *UI_WIDGET_TOOLS,
    # Context memory tools for conversation continuity
    *CONTEXT_MEMORY_TOOLS,
]


# Singleton instance for direct import
operations_agent = Agent(
    name="OperationsOptimizationAgent",
    model=get_routing_model(),
    description="COO / Operations Manager - Process improvement, bottleneck identification, rollout planning",
    instruction=OPERATIONS_AGENT_INSTRUCTION,
    tools=OPERATIONS_AGENT_TOOLS,
    generate_content_config=ROUTING_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_operations_agent(name_suffix: str = "") -> Agent:
    """Create a fresh OperationsOptimizationAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"OperationsOptimizationAgent{name_suffix}" if name_suffix else "OperationsOptimizationAgent"
    return Agent(
        name=agent_name,
        model=get_routing_model(),
        description="COO / Operations Manager - Process improvement, bottleneck identification, rollout planning",
        instruction=OPERATIONS_AGENT_INSTRUCTION,
        tools=OPERATIONS_AGENT_TOOLS,
        generate_content_config=ROUTING_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
