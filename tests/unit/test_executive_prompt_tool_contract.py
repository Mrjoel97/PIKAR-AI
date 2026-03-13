from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.agent import EXECUTIVE_INSTRUCTION, executive_agent
from app.agents.compliance import compliance_agent
from app.agents.content import content_agent
from app.agents.customer_support import customer_support_agent
from app.agents.data import data_agent
from app.agents.financial import financial_agent
from app.agents.hr import hr_agent
from app.agents.marketing import marketing_agent
from app.agents.operations import operations_agent
from app.agents.reporting import data_reporting_agent
from app.agents.sales import sales_agent
from app.agents.strategic import strategic_agent
from app.services.user_agent_factory import DEFAULT_EXECUTIVE_INSTRUCTION

EXECUTIVE_PROMPT_PATH = Path("app/prompts/executive_instruction.txt")
SKILL_TOOL_NAMES = {
    "list_skills",
    "use_skill",
    "search_skills",
    "get_skills_summary",
    "create_custom_skill",
    "list_user_skills",
    "list_available_skills",
}
REMOVED_PROMPT_REFERENCES = {"nano_banana", "nano-banana"}
SPECIALIST_AGENTS = [
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
    data_reporting_agent,
]
ALL_TOP_LEVEL_AGENTS = [executive_agent, *SPECIALIST_AGENTS]


def _tool_name(tool: object) -> str | None:
    if hasattr(tool, "__name__"):
        return getattr(tool, "__name__")
    if hasattr(tool, "name"):
        return getattr(tool, "name")
    return None


def _collect_recursive_tool_names(agent: object, seen: set[int] | None = None) -> set[str]:
    seen = seen or set()
    agent_id = id(agent)
    if agent_id in seen:
        return set()
    seen.add(agent_id)

    tool_names = {
        tool_name
        for tool in (getattr(agent, "tools", None) or [])
        for tool_name in [_tool_name(tool)]
        if tool_name
    }
    for sub_agent in getattr(agent, "sub_agents", None) or []:
        tool_names |= _collect_recursive_tool_names(sub_agent, seen)
    return tool_names


ALL_KNOWN_TOOL_NAMES = set().union(
    *(_collect_recursive_tool_names(agent) for agent in ALL_TOP_LEVEL_AGENTS)
)


def _mentioned_tool_names(instruction: str, tool_names: set[str]) -> set[str]:
    return {
        tool_name
        for tool_name in tool_names
        if re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(tool_name)}(?![A-Za-z0-9_])",
            instruction,
        )
    }


def test_executive_prompt_file_matches_factory_default() -> None:
    prompt_text = EXECUTIVE_PROMPT_PATH.read_text(encoding="utf-8")

    assert prompt_text == EXECUTIVE_INSTRUCTION
    assert prompt_text == DEFAULT_EXECUTIVE_INSTRUCTION


def test_executive_prompt_has_no_removed_nano_banana_references() -> None:
    lowered = EXECUTIVE_INSTRUCTION.lower()

    assert "nano-banana" not in lowered
    assert "nano_banana" not in lowered


def test_executive_prompt_references_only_accessible_tools() -> None:
    accessible = _collect_recursive_tool_names(executive_agent)
    referenced = _mentioned_tool_names(
        EXECUTIVE_INSTRUCTION,
        ALL_KNOWN_TOOL_NAMES | REMOVED_PROMPT_REFERENCES,
    )

    missing = referenced - accessible
    assert not missing, f"Executive prompt references unavailable tools: {sorted(missing)}"


@pytest.mark.parametrize("agent", SPECIALIST_AGENTS, ids=lambda agent: agent.name)
def test_all_specialist_agent_prompts_reference_only_available_tools(agent: object) -> None:
    accessible = _collect_recursive_tool_names(agent)
    referenced = _mentioned_tool_names(agent.instruction, ALL_KNOWN_TOOL_NAMES)

    missing = referenced - accessible
    assert not missing, f"{agent.name} prompt references unavailable tools: {sorted(missing)}"


@pytest.mark.parametrize("agent", SPECIALIST_AGENTS, ids=lambda agent: agent.name)
def test_specialist_agents_with_skill_tools_document_skill_usage(agent: object) -> None:
    accessible = _collect_recursive_tool_names(agent)
    exposed_skill_tools = accessible & SKILL_TOOL_NAMES
    if not exposed_skill_tools:
        pytest.skip(f"{agent.name} does not expose skill tools")

    documented = _mentioned_tool_names(agent.instruction, exposed_skill_tools)
    assert documented, f"{agent.name} exposes skill tools but does not document them"