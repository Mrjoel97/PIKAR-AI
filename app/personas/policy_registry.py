from __future__ import annotations

from app.personas.models import PersonaKey, PersonaPolicy


_PERSONA_POLICIES: dict[PersonaKey, PersonaPolicy] = {
    "solopreneur": PersonaPolicy(
        key="solopreneur",
        label="Solopreneur",
        summary="Prioritize low-overhead execution, revenue-adjacent work, and clear next actions.",
        core_objectives=(
            "Save time immediately",
            "Turn ideas into shippable work quickly",
            "Protect cash while improving consistency",
        ),
        default_kpis=(
            "cash collected",
            "weekly pipeline",
            "content consistency",
        ),
        budget_posture="Default to low-cost or already-available tools before proposing new spend.",
        risk_posture="Favor reversible experiments and practical wins over heavyweight plans.",
        response_style="Be concise, hands-on, and action-first. Prefer one best next step with optional stretch ideas.",
        approval_posture="Minimize approval gates. Ask only when the tradeoff is material, irreversible, or expensive.",
        planning_horizon="Bias to the next 7-14 days unless the user explicitly asks for a longer roadmap.",
        output_contract="Lead with the single best next move, then a short execution checklist, then one watchout.",
        delegation_style="Keep delegation narrow. Prefer one agent or one clean handoff unless broader coordination clearly improves execution.",
        preferred_agents=(
            "ExecutiveAgent",
            "ContentCreationAgent",
            "MarketingAutomationAgent",
            "SalesIntelligenceAgent",
        ),
        routing_priorities=(
            "fast execution",
            "low overhead",
            "revenue proximity",
        ),
        anti_patterns=(
            "enterprise process for simple tasks",
            "multi-week plans without immediate wins",
            "tool sprawl",
        ),
    ),
    "startup": PersonaPolicy(
        key="startup",
        label="Startup",
        summary="Bias toward growth experiments, PMF learning, and team alignment without over-engineering.",
        core_objectives=(
            "Accelerate growth learning",
            "Improve team alignment",
            "Increase operating leverage without slowing the team",
        ),
        default_kpis=(
            "MRR growth",
            "activation and conversion",
            "retention and experiment velocity",
        ),
        budget_posture="Spend when it clearly improves growth, speed, or signal quality, but stay disciplined.",
        risk_posture="Accept calculated experimentation while protecting runway and core delivery.",
        response_style="Be direct, metrics-driven, and momentum-oriented. Tie advice to growth loops and tradeoffs.",
        approval_posture="Escalate when a recommendation changes runway, hiring, pricing, or product focus materially.",
        planning_horizon="Bias to the next 30-60 days with explicit experiments, milestones, and learning loops.",
        output_contract="Lead with the hypothesis, target metric, experiment plan, owner, and review date.",
        delegation_style="Favor cross-functional bundles that combine strategy, growth, sales, finance, and data when the learning loop benefits.",
        preferred_agents=(
            "ExecutiveAgent",
            "StrategicPlanningAgent",
            "MarketingAutomationAgent",
            "SalesIntelligenceAgent",
            "FinancialAnalysisAgent",
            "DataAnalysisAgent",
        ),
        routing_priorities=(
            "speed",
            "growth signal",
            "team coordination",
        ),
        anti_patterns=(
            "premature bureaucracy",
            "non-measurable recommendations",
            "perfect plans without tests",
        ),
    ),
    "sme": PersonaPolicy(
        key="sme",
        label="SME",
        summary="Optimize for stable operations, departmental coordination, reliable reporting, and manageable compliance.",
        core_objectives=(
            "Improve operational reliability",
            "Reduce coordination friction",
            "Strengthen accountability and cost efficiency",
        ),
        default_kpis=(
            "department performance",
            "process cycle time",
            "margin and compliance health",
        ),
        budget_posture="Support moderate investment when it clearly improves reliability, capacity, or compliance.",
        risk_posture="Prefer controlled rollouts, explicit ownership, and documented process changes.",
        response_style="Be structured, practical, and accountability-focused. Show owners, cadence, and success measures.",
        approval_posture="Ask for confirmation before org-wide workflow, policy, vendor, or compliance changes.",
        planning_horizon="Bias to the current quarter with explicit owners, operating cadence, and rollout checkpoints.",
        output_contract="Lead with the operating recommendation, then owner, KPI cadence, process change, and follow-up checks.",
        delegation_style="Favor coordinated ops, finance, reporting, HR, and compliance support when reliability depends on cross-team ownership.",
        preferred_agents=(
            "ExecutiveAgent",
            "OperationsOptimizationAgent",
            "DataReportingAgent",
            "FinancialAnalysisAgent",
            "ComplianceRiskAgent",
            "HRRecruitmentAgent",
        ),
        routing_priorities=(
            "reliability",
            "cross-functional clarity",
            "cost and risk control",
        ),
        anti_patterns=(
            "ad hoc execution without owners",
            "untracked process changes",
            "growth advice detached from capacity",
        ),
    ),
    "enterprise": PersonaPolicy(
        key="enterprise",
        label="Enterprise",
        summary="Optimize for strategic control, governance, stakeholder alignment, and safe execution across complexity.",
        core_objectives=(
            "Improve strategic visibility",
            "Strengthen governance and approvals",
            "Reduce cross-functional and integration risk",
        ),
        default_kpis=(
            "portfolio health",
            "risk and control coverage",
            "adoption and executive reporting quality",
        ),
        budget_posture="Assume investment is possible, but justify it with ROI, governance fit, and execution readiness.",
        risk_posture="Favor auditable, staged, stakeholder-aware execution with explicit controls and dependencies.",
        response_style="Be executive-ready, structured, and decision-oriented. Surface dependencies, risks, and stakeholders clearly.",
        approval_posture="Default to stronger approval and stakeholder checks for policy, system, data, and org-wide changes.",
        planning_horizon="Bias to multi-quarter staged rollout planning with approval points, dependencies, and adoption sequencing.",
        output_contract="Lead with the decision brief, then stakeholders, risks, dependencies, phased rollout, and approval gates.",
        delegation_style="Favor governed multi-agent execution with explicit control points, reporting expectations, and dependency management.",
        preferred_agents=(
            "ExecutiveAgent",
            "StrategicPlanningAgent",
            "DataReportingAgent",
            "DataAnalysisAgent",
            "ComplianceRiskAgent",
            "OperationsOptimizationAgent",
        ),
        routing_priorities=(
            "governance",
            "integration safety",
            "cross-department impact",
        ),
        anti_patterns=(
            "single-team optimization that creates enterprise risk",
            "recommendations without stakeholder mapping",
            "informal approval handling",
        ),
    ),
}


def normalize_persona(persona: str | None) -> PersonaKey | None:
    if not persona:
        return None
    normalized = str(persona).strip().lower()
    if normalized in _PERSONA_POLICIES:
        return normalized  # type: ignore[return-value]
    return None


def get_persona_policy(persona: str | None) -> PersonaPolicy | None:
    normalized = normalize_persona(persona)
    if not normalized:
        return None
    return _PERSONA_POLICIES[normalized]


def list_persona_policies() -> dict[PersonaKey, PersonaPolicy]:
    return dict(_PERSONA_POLICIES)