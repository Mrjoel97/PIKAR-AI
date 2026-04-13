# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Research Intelligence Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.research.instructions import (
    RESEARCH_AGENT_DESCRIPTION,
    RESEARCH_AGENT_INSTRUCTION,
)
from app.agents.research.tools.adaptive_router import ADAPTIVE_ROUTER_TOOLS
from app.agents.research.tools.cost_tracker import COST_TRACKER_TOOLS
from app.agents.research.tools.graph_writer import GRAPH_WRITER_TOOLS
from app.agents.research.tools.monitoring_tools import MONITORING_TOOLS
from app.agents.research.tools.persona_synthesizer import PERSONA_SYNTHESIZER_TOOLS
from app.agents.research.tools.query_planner import QUERY_PLANNER_TOOLS
from app.agents.research.tools.synthesizer import SYNTHESIZER_TOOLS
from app.agents.research.tools.track_runner import TRACK_RUNNER_TOOLS
from app.agents.shared import DEEP_AGENT_CONFIG, get_model
from app.agents.tools.graph_tools import GRAPH_TOOLS

RESEARCH_AGENT_TOOLS = [
    *QUERY_PLANNER_TOOLS,
    *TRACK_RUNNER_TOOLS,
    *SYNTHESIZER_TOOLS,
    *GRAPH_WRITER_TOOLS,
    *COST_TRACKER_TOOLS,
    *GRAPH_TOOLS,
    *ADAPTIVE_ROUTER_TOOLS,
    # Continuous intelligence monitoring tools
    *MONITORING_TOOLS,
    # Phase 69: persona-aware synthesis
    *PERSONA_SYNTHESIZER_TOOLS,
]


def create_research_agent(
    name_suffix: str = "", output_key: str | None = None
) -> Agent:
    """Create a fresh ResearchAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.
        output_key: Optional output key for pipeline usage.

    Returns:
        A new Agent instance with no parent assignment.

    """
    agent_name = f"ResearchAgent{name_suffix}" if name_suffix else "ResearchAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description=RESEARCH_AGENT_DESCRIPTION,
        instruction=RESEARCH_AGENT_INSTRUCTION,
        tools=RESEARCH_AGENT_TOOLS,
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
    )


# Singleton instance for direct import (used by ExecutiveAgent sub_agents list)
research_agent = create_research_agent()
