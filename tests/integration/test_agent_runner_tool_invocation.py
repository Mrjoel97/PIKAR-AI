from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable

import pytest

from app.agent import executive_agent
from app.agents.compliance import create_compliance_agent
from app.agents.content import create_content_agent
from app.agents.customer_support import create_customer_support_agent
from app.agents.data import create_data_agent
from app.agents.financial import create_financial_agent
from app.agents.hr import create_hr_agent
from app.agents.marketing import create_marketing_agent
from app.agents.operations import create_operations_agent
from app.agents.reporting import create_data_reporting_agent
from app.agents.sales import create_sales_agent
from app.agents.strategic import create_strategic_agent

STOPWORDS = {
    "about",
    "and",
    "for",
    "from",
    "into",
    "just",
    "need",
    "our",
    "please",
    "show",
    "that",
    "the",
    "this",
    "with",
    "your",
}


@dataclass(frozen=True)
class RunnerScenario:
    name: str
    build_agent: Callable[[], object]
    prompt: str
    expected_tool: str
    expected_author: str


@dataclass
class AgentSnapshot:
    name: str
    instruction: str
    tools: list[Callable[..., dict]]
    sub_agents: list["AgentSnapshot"]


@dataclass(frozen=True)
class ToolCandidate:
    agent_name: str
    instruction: str
    tool: Callable[..., dict]


SCENARIOS = [
    RunnerScenario(
        name="ExecutiveAgent",
        build_agent=lambda: executive_agent,
        prompt="Display a revenue chart for this quarter.",
        expected_tool="create_revenue_chart_widget",
        expected_author="ExecutiveAgent",
    ),
    RunnerScenario(
        name="FinancialAnalysisAgent",
        build_agent=create_financial_agent,
        prompt="Get the current revenue stats for this month.",
        expected_tool="get_revenue_stats",
        expected_author="FinancialAnalysisAgent",
    ),
    RunnerScenario(
        name="ContentCreationAgent",
        build_agent=create_content_agent,
        prompt="Create a high-quality video ad campaign with premium promo content for our new product launch.",
        expected_tool="execute_content_pipeline",
        expected_author="VideoDirectorAgent",
    ),
    RunnerScenario(
        name="StrategicPlanningAgent",
        build_agent=create_strategic_agent,
        prompt="Start an initiative from this business idea for a new B2B workflow product.",
        expected_tool="start_initiative_from_idea",
        expected_author="InitiativeOpsAgent",
    ),
    RunnerScenario(
        name="SalesIntelligenceAgent",
        build_agent=create_sales_agent,
        prompt="List my sales follow-up tasks.",
        expected_tool="list_tasks",
        expected_author="SalesIntelligenceAgent",
    ),
    RunnerScenario(
        name="MarketingAutomationAgent",
        build_agent=create_marketing_agent,
        prompt="List our current campaigns.",
        expected_tool="list_campaigns",
        expected_author="MarketingAutomationAgent",
    ),
    RunnerScenario(
        name="OperationsOptimizationAgent",
        build_agent=create_operations_agent,
        prompt="List current inventory items and stock levels.",
        expected_tool="list_inventory",
        expected_author="OperationsOptimizationAgent",
    ),
    RunnerScenario(
        name="HRRecruitmentAgent",
        build_agent=create_hr_agent,
        prompt="List open jobs for the hiring team.",
        expected_tool="list_jobs",
        expected_author="HRRecruitmentAgent",
    ),
    RunnerScenario(
        name="ComplianceRiskAgent",
        build_agent=create_compliance_agent,
        prompt="List all active risks in the register.",
        expected_tool="list_risks",
        expected_author="ComplianceRiskAgent",
    ),
    RunnerScenario(
        name="CustomerSupportAgent",
        build_agent=create_customer_support_agent,
        prompt="List open support tickets that need attention.",
        expected_tool="list_tickets",
        expected_author="CustomerSupportAgent",
    ),
    RunnerScenario(
        name="DataAnalysisAgent",
        build_agent=create_data_agent,
        prompt="List saved analytics reports.",
        expected_tool="list_reports",
        expected_author="DataAnalysisAgent",
    ),
    RunnerScenario(
        name="DataReportingAgent",
        build_agent=create_data_reporting_agent,
        prompt="List report schedules for weekly summaries.",
        expected_tool="list_report_schedules",
        expected_author="DataReportingAgent",
    ),
]


def _tool_name(tool: object) -> str:
    return getattr(tool, "__name__", getattr(tool, "name", str(tool)))


def _make_stub(tool_name: str) -> Callable[..., dict]:
    def _stub(prompt: str | None = None, **kwargs: object) -> dict:
        return {
            "success": True,
            "tool_name": tool_name,
            "prompt": prompt,
            "kwargs": kwargs,
        }

    _stub.__name__ = tool_name
    return _stub


def _snapshot_agent(agent: object, seen: set[int] | None = None) -> AgentSnapshot:
    seen = seen or set()
    agent_id = id(agent)
    if agent_id in seen:
        return AgentSnapshot(
            name=getattr(agent, "name", "UnknownAgent"),
            instruction=getattr(agent, "instruction", ""),
            tools=[],
            sub_agents=[],
        )
    seen.add(agent_id)

    return AgentSnapshot(
        name=getattr(agent, "name", "UnknownAgent"),
        instruction=getattr(agent, "instruction", ""),
        tools=[_make_stub(_tool_name(tool)) for tool in (getattr(agent, "tools", None) or [])],
        sub_agents=[_snapshot_agent(sub_agent, seen) for sub_agent in (getattr(agent, "sub_agents", None) or [])],
    )


def _collect_candidates(agent: AgentSnapshot) -> list[ToolCandidate]:
    candidates = [
        ToolCandidate(agent_name=agent.name, instruction=agent.instruction, tool=tool)
        for tool in agent.tools
    ]
    for sub_agent in agent.sub_agents:
        candidates.extend(_collect_candidates(sub_agent))
    return candidates


def _normalize_token(token: str) -> str:
    return token.rstrip("s")


def _tokenize(text: str) -> set[str]:
    return {
        _normalize_token(token)
        for token in re.findall(r"[a-z0-9_]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def _instruction_context(instruction: str, tool_name: str) -> str:
    matching_lines = [line.strip() for line in instruction.splitlines() if tool_name in line]
    return " ".join(matching_lines) or tool_name.replace("_", " ")


def _score_candidate(prompt: str, candidate: ToolCandidate) -> int:
    prompt_tokens = _tokenize(prompt)
    tool_tokens = {_normalize_token(part) for part in candidate.tool.__name__.split("_") if part}
    instruction_tokens = _tokenize(_instruction_context(candidate.instruction, candidate.tool.__name__))
    exact_name_bonus = 10 if candidate.tool.__name__ in prompt else 0

    return exact_name_bonus + (4 * len(prompt_tokens & tool_tokens)) + (2 * len(prompt_tokens & instruction_tokens))


class OfflineToolChoosingRunner:
    """Deterministic runner-shaped harness for tool selection coverage.

    This keeps the test offline and repeatable while still exercising the real
    agent graph, instructions, delegation structure, and registered tool names.
    """

    def __init__(self, root_agent: object):
        self.root_agent = _snapshot_agent(root_agent)

    def run(self, prompt: str) -> list[dict[str, object]]:
        candidates = _collect_candidates(self.root_agent)
        ranked = sorted(
            ((candidate, _score_candidate(prompt, candidate)) for candidate in candidates),
            key=lambda item: item[1],
            reverse=True,
        )
        best_candidate, best_score = ranked[0]
        assert best_score > 0, f"No tool matched prompt: {prompt}"

        result = best_candidate.tool(prompt=prompt)
        events: list[dict[str, object]] = []
        if best_candidate.agent_name != self.root_agent.name:
            events.append(
                {
                    "event_type": "delegation",
                    "author": self.root_agent.name,
                    "delegate": best_candidate.agent_name,
                }
            )
        events.append(
            {
                "event_type": "tool_call",
                "author": best_candidate.agent_name,
                "tool_name": best_candidate.tool.__name__,
                "result": result,
            }
        )
        events.append(
            {
                "event_type": "tool_response",
                "author": best_candidate.agent_name,
                "tool_name": best_candidate.tool.__name__,
                "result": result,
            }
        )
        return events


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario.name)
def test_top_level_agent_runner_invokes_expected_tool(scenario: RunnerScenario) -> None:
    agent = scenario.build_agent()
    runner = OfflineToolChoosingRunner(agent)

    events = runner.run(scenario.prompt)
    tool_calls = [event for event in events if event["event_type"] == "tool_call"]

    assert tool_calls, "Expected a tool_call event"
    tool_call = tool_calls[-1]
    assert tool_call["tool_name"] == scenario.expected_tool
    assert tool_call["author"] == scenario.expected_author
    assert tool_call["result"]["success"] is True

    if scenario.expected_author != getattr(agent, "name", scenario.expected_author):
        assert any(
            event["event_type"] == "delegation" and event["delegate"] == scenario.expected_author
            for event in events
        ), f"Expected delegation to {scenario.expected_author}"
