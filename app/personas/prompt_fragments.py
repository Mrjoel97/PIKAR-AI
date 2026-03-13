from __future__ import annotations

from typing import Any

from app.personas.policy_registry import get_persona_policy


_AGENT_PERSONA_FOCUS: dict[str, dict[str, str]] = {
    "ExecutiveAgent": {
        "solopreneur": "Route toward the fewest moving parts possible. Prefer direct execution, immediate revenue or time savings, and a single practical next step.",
        "startup": "Route toward growth, validation, and team alignment. Favor measurable experiments, PMF learning, and cross-functional momentum.",
        "sme": "Route toward operational clarity, reliable reporting, and controlled execution. Favor owners, cadence, and process stability.",
        "enterprise": "Route toward stakeholder-aware execution, governance, and strategic visibility. Surface approvals, dependencies, and risk controls.",
    },
    "FinancialAnalysisAgent": {
        "solopreneur": "Focus on cash discipline, pricing, invoice collection, and the smallest financial model that improves decisions this week.",
        "startup": "Focus on runway, burn, growth efficiency, scenario planning, and finance views that support PMF, fundraising, and hiring tradeoffs.",
        "sme": "Focus on margin control, departmental accountability, budget variance, and reporting that improves steady operational performance.",
        "enterprise": "Focus on board-ready narratives, portfolio tradeoffs, controls, forecast confidence, and financially material dependencies.",
    },
    "ContentCreationAgent": {
        "solopreneur": "Create lean, high-leverage content systems the user can actually sustain alone. Favor repurposing and fast publishing.",
        "startup": "Create content that accelerates learning, demand generation, launches, and positioning. Tie deliverables to funnel stage and experiments.",
        "sme": "Create content that supports brand consistency, customer trust, and repeatable campaigns across a broader operating rhythm.",
        "enterprise": "Create content that is stakeholder-safe, governance-aware, and suitable for multi-audience distribution with clear review expectations.",
    },
    "StrategicPlanningAgent": {
        "solopreneur": "Turn strategy into practical milestones the owner can execute without building an internal bureaucracy.",
        "startup": "Prioritize PMF, growth loops, speed of learning, and strategic sequencing around scarce time and runway.",
        "sme": "Prioritize operating leverage, departmental coordination, and roadmaps that improve execution quality and accountability.",
        "enterprise": "Prioritize portfolio thinking, transformation sequencing, stakeholder alignment, and governance across complex initiatives.",
    },
    "SalesIntelligenceAgent": {
        "solopreneur": "Focus on simple pipeline movement, fast follow-up, and offers that directly convert into cash or meetings.",
        "startup": "Focus on repeatable pipeline creation, ICP refinement, objection learning, and metrics that improve conversion.",
        "sme": "Focus on sales process consistency, account coverage, forecasting discipline, and handoffs across teams.",
        "enterprise": "Focus on multi-stakeholder deal motion, executive narratives, risk handling, and complex account planning.",
    },
    "MarketingAutomationAgent": {
        "solopreneur": "Favor low-cost channels, lightweight automations, and campaigns the user can maintain without a large team.",
        "startup": "Favor growth experiments, funnel metrics, launch velocity, and automations that increase learning speed.",
        "sme": "Favor repeatable campaign operations, segmentation, reporting discipline, and efficient use of budget across channels.",
        "enterprise": "Favor governed campaigns, audience coordination, channel compliance, and integrations with clear approval paths.",
    },
    "OperationsOptimizationAgent": {
        "solopreneur": "Automate repetitive work quickly and keep process design lightweight. Avoid suggesting enterprise operating systems for solo workflows.",
        "startup": "Build fast, scalable handoffs and operating cadences that support speed without adding too much drag.",
        "sme": "Emphasize SOPs, ownership, workflow reliability, and vendor or cross-team coordination.",
        "enterprise": "Emphasize rollout planning, control points, integration dependencies, and change management.",
    },
    "HRRecruitmentAgent": {
        "solopreneur": "Focus on the first hires, contractor leverage, and lightweight people processes that do not create admin overload.",
        "startup": "Focus on speed, role clarity, talent density, and hiring choices that improve execution without wasting runway.",
        "sme": "Focus on recruitment throughput, policy consistency, manager enablement, and stable team operations.",
        "enterprise": "Focus on governance, fairness, stakeholder alignment, and repeatable hiring or people operations at scale.",
    },
    "ComplianceRiskAgent": {
        "solopreneur": "Recommend the minimum viable compliance posture that reduces meaningful risk without drowning the user in legal overhead.",
        "startup": "Focus on readiness for growth, contracts, data handling, and foundational controls that support future scale.",
        "sme": "Focus on audit cadence, policy enforcement, vendor risk, and compliance operations that fit a multi-team business.",
        "enterprise": "Focus on control frameworks, approvals, data governance, auditability, and executive risk communication.",
    },
    "CustomerSupportAgent": {
        "solopreneur": "Favor fast, empathetic support systems and simple knowledge capture the founder can maintain.",
        "startup": "Favor insights that improve retention, reduce churn, and turn support feedback into product or growth learning.",
        "sme": "Favor queue discipline, SLA clarity, repeatable processes, and team visibility.",
        "enterprise": "Favor segmentation, escalation governance, executive visibility, and risk-aware support operations.",
    },
    "DataAnalysisAgent": {
        "solopreneur": "Focus on a few high-signal metrics that directly guide weekly decisions. Avoid analytics sprawl.",
        "startup": "Focus on growth, activation, retention, experiment readouts, and fast learning from imperfect data.",
        "sme": "Focus on operational performance, departmental comparisons, and decision support tied to efficiency and reliability.",
        "enterprise": "Focus on portfolio-level visibility, executive reporting quality, and analysis that accounts for dependencies and controls.",
    },
    "DataReportingAgent": {
        "solopreneur": "Produce lean reports with only the metrics and actions the owner can use immediately.",
        "startup": "Produce decision-ready reports that support experiment cadence, team alignment, and investor-ready storytelling when needed.",
        "sme": "Produce recurring operational reports with owners, trends, and clear actions for managers.",
        "enterprise": "Produce executive-ready reporting with stronger structure, governance cues, stakeholder framing, and audit-friendly organization.",
    },
}

_AGENT_DELIVERABLE_SHAPES: dict[str, dict[str, str]] = {
    "ExecutiveAgent": {
        "solopreneur": "Return one recommended route, a 3-step execution list, and one watchout. Do not give a broad strategy deck unless asked.",
        "startup": "Return a growth memo with the hypothesis, experiment plan, owner, target metric, and review date.",
        "sme": "Return an operating plan with owner by function, KPI cadence, rollout steps, and accountability checkpoints.",
        "enterprise": "Return a decision brief with stakeholders, approvals, dependencies, risks, and phased rollout notes.",
    },
    "FinancialAnalysisAgent": {
        "solopreneur": "Return a cash snapshot, the one highest-leverage financial action, and the main risk to watch this week.",
        "startup": "Return runway, burn, growth efficiency, scenario assumptions, and the next finance-sensitive decision.",
        "sme": "Return margin or variance findings, owner-level follow-up, KPI cadence, and process or budget actions.",
        "enterprise": "Return an executive summary, scenario comparisons, control implications, and financially material dependencies.",
    },
    "ContentCreationAgent": {
        "solopreneur": "Return a lightweight publishing plan, repurposing map, and the one content asset to ship first.",
        "startup": "Return message angle, funnel stage, test variants, distribution hypothesis, and success metric.",
        "sme": "Return a repeatable campaign package with calendar, owner handoff, brand guardrails, and deliverables.",
        "enterprise": "Return an audience matrix, review workflow, governance notes, and channel-specific deliverables.",
    },
    "StrategicPlanningAgent": {
        "solopreneur": "Return a short milestone plan with the next decision, immediate actions, and what to defer.",
        "startup": "Return a PMF or growth roadmap with hypotheses, sequencing, owners, and learning checkpoints.",
        "sme": "Return a quarterly roadmap with department owners, operating changes, KPIs, and rollout order.",
        "enterprise": "Return a portfolio roadmap with workstreams, stakeholders, governance gates, and dependency map.",
    },
    "SalesIntelligenceAgent": {
        "solopreneur": "Return the next best offer, follow-up sequence, and simple pipeline moves that convert into cash or meetings.",
        "startup": "Return ICP learning, pipeline experiment ideas, objection themes, and conversion metrics to track.",
        "sme": "Return sales process fixes, forecast implications, team handoffs, and owner-based next actions.",
        "enterprise": "Return account strategy, stakeholder map, risk handling plan, and executive narrative for the deal.",
    },
    "MarketingAutomationAgent": {
        "solopreneur": "Return one maintainable campaign, one automation, channel choice, and the metric to review next.",
        "startup": "Return experiment backlog, funnel metric target, launch motion, and rapid iteration cadence.",
        "sme": "Return campaign calendar, segmentation logic, budget use, reporting cadence, and handoff owners.",
        "enterprise": "Return governed campaign plan, audience coordination notes, compliance checks, and approval path.",
    },
    "OperationsOptimizationAgent": {
        "solopreneur": "Return the process shortcut, tool or automation to add, expected time saved, and one caveat.",
        "startup": "Return scalable handoff design, operating cadence, owner map, and friction points to remove now.",
        "sme": "Return SOP or workflow change, rollout owner, KPI, risk controls, and follow-up review cadence.",
        "enterprise": "Return change plan, control points, integration dependencies, stakeholder impacts, and rollout stages.",
    },
    "HRRecruitmentAgent": {
        "solopreneur": "Return the next hiring move, role scope, lightweight process, and capacity impact.",
        "startup": "Return role definition, hiring tradeoff, speed plan, success scorecard, and runway implication.",
        "sme": "Return recruiting workflow, manager responsibilities, policy considerations, and throughput metrics.",
        "enterprise": "Return stakeholder-aligned hiring plan, governance checkpoints, fairness considerations, and scaling notes.",
    },
    "ComplianceRiskAgent": {
        "solopreneur": "Return the minimum viable control set, what to do now, what can wait, and the biggest exposure.",
        "startup": "Return readiness gaps, near-term controls, contract or data risks, and the next checkpoint for scale.",
        "sme": "Return audit or policy actions, owner assignments, vendor or process risks, and review cadence.",
        "enterprise": "Return control mapping, governance implications, approval needs, and executive risk summary.",
    },
    "CustomerSupportAgent": {
        "solopreneur": "Return the fastest support fix, reusable answer, and the customer insight to capture immediately.",
        "startup": "Return churn or retention insight, feedback loop into product, and queue actions to test.",
        "sme": "Return SLA or queue improvements, owner visibility, process change, and recurring issue pattern.",
        "enterprise": "Return segmented support plan, escalation path, governance note, and executive risk signals.",
    },
    "DataAnalysisAgent": {
        "solopreneur": "Return the few metrics that matter this week, what changed, and the decision they should drive now.",
        "startup": "Return experiment readout, funnel implications, data caveats, and next metric to instrument or monitor.",
        "sme": "Return operational KPI analysis, department comparisons, owner follow-up, and efficiency implications.",
        "enterprise": "Return executive-level analysis, dependency-aware interpretation, confidence caveats, and control implications.",
    },
    "DataReportingAgent": {
        "solopreneur": "Return a lean scorecard with immediate actions and no excess reporting overhead.",
        "startup": "Return a decision-ready report with growth metrics, experiment cadence, and investor-ready framing when relevant.",
        "sme": "Return a recurring management report with owners, trends, actions, and review cadence.",
        "enterprise": "Return an executive report with governance cues, stakeholder framing, audit-friendly structure, and phased actions.",
    },
}

_AGENT_ALIASES = {
    "VideoDirectorAgent": "ContentCreationAgent",
    "GraphicDesignerAgent": "ContentCreationAgent",
    "CopywriterAgent": "ContentCreationAgent",
    "FinancialReportAgent": "FinancialAnalysisAgent",
    "LeadScoringAgent": "SalesIntelligenceAgent",
    "RiskReportAgent": "ComplianceRiskAgent",
    "DataInsightAgent": "DataAnalysisAgent",
    "ReportGeneratorAgent": "DataReportingAgent",
    "StrategicInsightAgent": "StrategicPlanningAgent",
    "ExecutionArchitectAgent": "StrategicPlanningAgent",
    "MarketAnalystAgent": "StrategicPlanningAgent",
    "CompetitiveResearcherAgent": "StrategicPlanningAgent",
    "ConsumerExpertAgent": "StrategicPlanningAgent",
}


def resolve_agent_name(agent_name: str | None) -> str | None:
    if not agent_name:
        return None
    raw = str(agent_name).strip()
    if not raw:
        return None

    for alias, canonical in _AGENT_ALIASES.items():
        if raw == alias or raw.startswith(f"{alias}_"):
            return canonical

    for canonical in _AGENT_PERSONA_FOCUS:
        if raw == canonical or raw.startswith(f"{canonical}_"):
            return canonical

    return raw



def _get_agent_persona_entry(
    mapping: dict[str, dict[str, str]],
    agent_name: str | None,
    persona: str | None,
) -> str:
    normalized_agent = resolve_agent_name(agent_name)
    if not normalized_agent or not persona:
        return ""
    return mapping.get(normalized_agent, {}).get(str(persona).strip().lower(), "")



def build_agent_persona_fragment(agent_name: str | None, persona: str | None) -> str:
    focus = _get_agent_persona_entry(_AGENT_PERSONA_FOCUS, agent_name, persona)
    deliverable_shape = _get_agent_persona_entry(_AGENT_DELIVERABLE_SHAPES, agent_name, persona)
    if not focus and not deliverable_shape:
        return ""

    lines: list[str] = []
    if focus:
        lines.append(f"- Strategic focus: {focus}")
    if deliverable_shape:
        lines.append(f"- Deliverable shape: {deliverable_shape}")
    return "\n".join(lines)



def build_persona_policy_block(
    persona: str | None,
    *,
    agent_name: str | None = None,
    include_routing: bool = True,
) -> str:
    policy = get_persona_policy(persona)
    if not policy:
        return ""

    lines = [
        f"## ACTIVE PERSONA POLICY: {policy.label.upper()}",
        f"- Summary: {policy.summary}",
        f"- Core objectives: {', '.join(policy.core_objectives)}",
        f"- Default KPIs: {', '.join(policy.default_kpis)}",
        f"- Budget posture: {policy.budget_posture}",
        f"- Risk posture: {policy.risk_posture}",
        f"- Response style: {policy.response_style}",
        f"- Approval posture: {policy.approval_posture}",
        f"- Planning horizon: {policy.planning_horizon}",
        f"- Output contract: {policy.output_contract}",
        f"- Delegation style: {policy.delegation_style}",
        f"- Avoid: {', '.join(policy.anti_patterns)}",
    ]

    if include_routing:
        lines.append(f"- Preferred agents: {', '.join(policy.preferred_agents)}")
        lines.append(f"- Routing priorities: {', '.join(policy.routing_priorities)}")

    agent_fragment = build_agent_persona_fragment(agent_name, persona)
    if agent_fragment:
        lines.append("")
        lines.append("## HOW TO ADAPT IN THIS ROLE")
        lines.extend(agent_fragment.splitlines())

    return "\n".join(lines)



def build_delegation_handoff_fragment(persona: str | None, target_agent_name: str | None) -> str:
    policy = get_persona_policy(persona)
    if not policy:
        return ""

    role_focus = _get_agent_persona_entry(_AGENT_PERSONA_FOCUS, target_agent_name, persona)
    deliverable_shape = _get_agent_persona_entry(_AGENT_DELIVERABLE_SHAPES, target_agent_name, persona)
    lines = [
        "[DELEGATION CONTRACT]",
        f"Persona: {policy.label}",
        f"Prioritize: {', '.join(policy.routing_priorities)}",
        f"Planning horizon: {policy.planning_horizon}",
        f"Output contract: {policy.output_contract}",
        f"Approval posture: {policy.approval_posture}",
        f"Delegation style: {policy.delegation_style}",
    ]
    if role_focus:
        lines.append(f"Target role focus: {role_focus}")
    if deliverable_shape:
        lines.append(f"Target deliverable: {deliverable_shape}")
    lines.append("[END DELEGATION CONTRACT]")
    return "\n".join(lines)