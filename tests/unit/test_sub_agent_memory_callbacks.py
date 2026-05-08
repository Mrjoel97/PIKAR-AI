# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Regression test: every sub-sub-agent must register both context-memory callbacks.

Background
----------
"Sub-sub-agents" are the deeper layer below specialist agents (e.g.,
VideoDirectorAgent under ContentCreationAgent, CampaignAgent under
MarketingAutomationAgent). When one of these forgets to register
``context_memory_before_model_callback`` or ``context_memory_after_tool_callback``,
the user's accumulated context (brand, audience, recent facts) silently fails to
load into the model prompt — so the agent re-asks for information it should
already have, breaking multi-turn UX.

This regression existed historically in the content sub-agents (see header
comment in ``app/agents/content/agent.py``) and was caught only after users
complained. This test wires it shut permanently.

Exceptions
----------
ADK forbids ``before_model_callback`` and ``after_tool_callback`` on agents
declared with ``output_schema=...`` (those agents run in pure structured-JSON
mode with ``include_contents="none"``). For these, the parent agent carries
the user context and the typed sub-agent only emits the schema-bound payload.
Such agents are listed in ``OUTPUT_SCHEMA_EXCEPTIONS`` below with a reason
string and skipped from the callback assertion.
"""

from __future__ import annotations

from typing import Any, Callable

import pytest

# Sub-sub-agents that MUST have both context_memory_before_model_callback and
# context_memory_after_tool_callback. Each tuple is (label, factory) where
# factory is a zero-arg callable returning a freshly built agent instance —
# we use factories (not direct singleton imports) so the test exercises the
# same construction path that runtime delegation triggers.
SUB_SUB_AGENTS_REQUIRING_CALLBACKS: list[tuple[str, Callable[[], Any]]] = [
    # ---- Content sub-agents (the original regression site) ----
    (
        "VideoDirectorAgent",
        lambda: __import__(
            "app.agents.content.agent", fromlist=["_create_video_director"]
        )._create_video_director(),
    ),
    (
        "GraphicDesignerAgent",
        lambda: __import__(
            "app.agents.content.agent", fromlist=["_create_graphic_designer"]
        )._create_graphic_designer(),
    ),
    (
        "CopywriterAgent",
        lambda: __import__(
            "app.agents.content.agent", fromlist=["_create_copywriter"]
        )._create_copywriter(),
    ),
    # ---- Operations ----
    (
        "ConfigurationAgent",
        lambda: __import__(
            "app.agents.operations.agent", fromlist=["_create_config_agent"]
        )._create_config_agent(),
    ),
    # ---- Data ----
    (
        "SheetsAgent",
        lambda: __import__(
            "app.agents.data.agent", fromlist=["_create_sheets_agent"]
        )._create_sheets_agent(),
    ),
    # ---- Strategic sub-agents (factory-built) ----
    (
        "KnowledgeVaultAgent",
        lambda: __import__(
            "app.agents.strategic.agent", fromlist=["_create_knowledge_agent"]
        )._create_knowledge_agent(),
    ),
    (
        "InitiativeOpsAgent",
        lambda: __import__(
            "app.agents.strategic.agent", fromlist=["_create_initiative_ops_agent"]
        )._create_initiative_ops_agent(),
    ),
    # ---- Strategic research/braindump sub-sub-agents ----
    (
        "BraindumpTranscriber",
        lambda: __import__(
            "app.agents.strategic.subagents",
            fromlist=["create_braindump_transcriber"],
        ).create_braindump_transcriber(),
    ),
    (
        "StrategicInsightAgent",
        lambda: __import__(
            "app.agents.strategic.subagents",
            fromlist=["create_braindump_insight_agent"],
        ).create_braindump_insight_agent(),
    ),
    (
        "ExecutionArchitectAgent",
        lambda: __import__(
            "app.agents.strategic.subagents", fromlist=["create_action_item_agent"]
        ).create_action_item_agent(),
    ),
    (
        "MarketAnalystAgent",
        lambda: __import__(
            "app.agents.strategic.subagents", fromlist=["create_market_analyst_agent"]
        ).create_market_analyst_agent(),
    ),
    (
        "CompetitiveResearcherAgent",
        lambda: __import__(
            "app.agents.strategic.subagents",
            fromlist=["create_competitive_researcher_agent"],
        ).create_competitive_researcher_agent(),
    ),
    (
        "ConsumerExpertAgent",
        lambda: __import__(
            "app.agents.strategic.subagents", fromlist=["create_consumer_expert_agent"]
        ).create_consumer_expert_agent(),
    ),
    # ---- Marketing sub-agents (6 specialists) ----
    (
        "CampaignAgent",
        lambda: __import__(
            "app.agents.marketing.agent", fromlist=["_create_campaign_agent"]
        )._create_campaign_agent(),
    ),
    (
        "EmailMarketingAgent",
        lambda: __import__(
            "app.agents.marketing.agent", fromlist=["_create_email_agent"]
        )._create_email_agent(),
    ),
    (
        "AdPlatformAgent",
        lambda: __import__(
            "app.agents.marketing.agent", fromlist=["_create_ad_agent"]
        )._create_ad_agent(),
    ),
    (
        "AudienceAgent",
        lambda: __import__(
            "app.agents.marketing.agent", fromlist=["_create_audience_agent"]
        )._create_audience_agent(),
    ),
    (
        "SEOAgent",
        lambda: __import__(
            "app.agents.marketing.agent", fromlist=["_create_seo_agent"]
        )._create_seo_agent(),
    ),
    (
        "SocialMediaAgent",
        lambda: __import__(
            "app.agents.marketing.agent", fromlist=["_create_social_agent"]
        )._create_social_agent(),
    ),
    # ---- Admin sub-agents (5 specialists) ----
    (
        "SystemHealthAgent",
        lambda: __import__(
            "app.agents.admin.agent", fromlist=["_create_system_health_agent"]
        )._create_system_health_agent(),
    ),
    (
        "UserManagementAgent",
        lambda: __import__(
            "app.agents.admin.agent", fromlist=["_create_user_management_agent"]
        )._create_user_management_agent(),
    ),
    (
        "BillingAgent",
        lambda: __import__(
            "app.agents.admin.agent", fromlist=["_create_billing_agent"]
        )._create_billing_agent(),
    ),
    (
        "GovernanceAgent",
        lambda: __import__(
            "app.agents.admin.agent", fromlist=["_create_governance_agent"]
        )._create_governance_agent(),
    ),
    (
        "KnowledgeAgent (admin)",
        lambda: __import__(
            "app.agents.admin.agent", fromlist=["_create_knowledge_agent"]
        )._create_knowledge_agent(),
    ),
]


# Sub-sub-agents that intentionally lack callbacks because they declare
# `output_schema=...` and `include_contents="none"` — ADK forbids
# before_model_callback / after_tool_callback in this configuration. The
# parent agent carries the user context; the typed sub-agent only emits the
# schema-bound payload.
OUTPUT_SCHEMA_EXCEPTIONS: list[tuple[str, str, str]] = [
    (
        "RiskReportAgent",
        "app.agents.compliance.agent.risk_report_agent",
        "output_schema=RiskAssessment with include_contents='none'",
    ),
    (
        "LeadScoringAgent",
        "app.agents.sales.agent.lead_scoring_agent",
        "output_schema=LeadQualification with include_contents='none'",
    ),
    (
        "DataInsightAgent",
        "app.agents.data.agent.data_insight_agent",
        "output_schema=DataInsight with include_contents='none'",
    ),
    (
        "ReportGeneratorAgent",
        "app.agents.reporting.agent.report_generator_agent",
        "output_schema=DataInsight with include_contents='none'",
    ),
    (
        "FinancialReportAgent",
        "app.agents.financial.agent.financial_report_agent",
        "output_schema=FinancialReport with include_contents='none'",
    ),
]


def _get_agent_kwargs(agent: Any) -> dict:
    """Extract constructor kwargs stored by ADK BaseModel / MockAgent.

    Both the real PikarAgent (ADK) and the unit-test MockAgent stash original
    kwargs in ``__dict__['_kwargs']``. This is the most reliable way to verify
    the callbacks were passed at construction time, since attribute access on
    ADK models can hide ``None`` values vs. unset values.
    """
    return agent.__dict__.get("_kwargs", {})


@pytest.mark.parametrize(
    "label,factory",
    SUB_SUB_AGENTS_REQUIRING_CALLBACKS,
    ids=[label for label, _ in SUB_SUB_AGENTS_REQUIRING_CALLBACKS],
)
def test_sub_sub_agent_has_before_model_callback(label: str, factory: Callable[[], Any]):
    """Every non-output_schema sub-sub-agent must register before_model_callback."""
    agent = factory()
    kwargs = _get_agent_kwargs(agent)
    cb = kwargs.get("before_model_callback")
    assert cb is not None, (
        f"{label} is missing before_model_callback — user context (brand, "
        f"audience, prior facts) will silently fail to load into prompts. "
        f"Add before_model_callback=context_memory_before_model_callback "
        f"to the Agent(...) constructor."
    )


@pytest.mark.parametrize(
    "label,factory",
    SUB_SUB_AGENTS_REQUIRING_CALLBACKS,
    ids=[label for label, _ in SUB_SUB_AGENTS_REQUIRING_CALLBACKS],
)
def test_sub_sub_agent_has_after_tool_callback(label: str, factory: Callable[[], Any]):
    """Every non-output_schema sub-sub-agent must register after_tool_callback."""
    agent = factory()
    kwargs = _get_agent_kwargs(agent)
    cb = kwargs.get("after_tool_callback")
    assert cb is not None, (
        f"{label} is missing after_tool_callback — facts saved via tools "
        f"(save_user_context, etc.) will not be persisted to session state. "
        f"Add after_tool_callback=context_memory_after_tool_callback "
        f"to the Agent(...) constructor."
    )


@pytest.mark.parametrize(
    "label,import_path,reason",
    OUTPUT_SCHEMA_EXCEPTIONS,
    ids=[label for label, _, _ in OUTPUT_SCHEMA_EXCEPTIONS],
)
def test_output_schema_sub_sub_agent_exception_documented(
    label: str, import_path: str, reason: str
):
    """Sub-sub-agents declared as exceptions must indeed have output_schema set.

    If a future refactor removes ``output_schema`` from one of these agents
    without also adding the context-memory callbacks, this test makes it
    impossible to silently regress: either the agent stays an exception (keeps
    output_schema) or it must be moved to ``SUB_SUB_AGENTS_REQUIRING_CALLBACKS``
    and gain the callbacks.
    """
    module_path, _, attr = import_path.rpartition(".")
    module = __import__(module_path, fromlist=[attr])
    agent = getattr(module, attr)
    kwargs = _get_agent_kwargs(agent)

    assert kwargs.get("output_schema") is not None, (
        f"{label} is listed as an output_schema exception ({reason}) but its "
        f"constructor did NOT receive output_schema. Either add output_schema "
        f"back, or remove {label} from OUTPUT_SCHEMA_EXCEPTIONS and add the "
        f"two context-memory callbacks."
    )
