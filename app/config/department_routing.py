# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Department routing configuration for SME department coordination.

Maps business department types to their specialist agent names and keyword
patterns used to detect the department from a natural-language query.

Exports:
    DEPARTMENT_ROUTING: dict mapping department type to DepartmentRoute.
    detect_department: function that maps a query string to (dept_type, agent_name).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DepartmentRoute:
    """Routing configuration for a single business department.

    Attributes:
        agent_name: The ADK agent class name to delegate to.
        display_name: Human-readable department label.
        keywords: List of keyword/phrase patterns that signal this department.
    """

    agent_name: str
    display_name: str
    keywords: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core routing table
# ---------------------------------------------------------------------------
# Keys match the department type values seeded in the DB:
#   SALES, MARKETING, CONTENT, STRATEGIC, DATA, FINANCIAL, SUPPORT,
#   HR, COMPLIANCE, OPERATIONS
# ---------------------------------------------------------------------------

DEPARTMENT_ROUTING: dict[str, DepartmentRoute] = {
    "FINANCIAL": DepartmentRoute(
        agent_name="FinancialAnalysisAgent",
        display_name="Finance & Treasury",
        keywords=[
            "revenue",
            "budget",
            "expense",
            "invoice",
            "p&l",
            "profit",
            "loss",
            "forecast",
            "cash flow",
            "burn rate",
            "financial",
            "accounting",
            "balance sheet",
            "roi",
            "cost",
            "pricing",
            "tax",
            "treasury",
            "fiscal",
            "payables",
            "receivables",
            "ledger",
            "bookkeeping",
            "audit",
            "quarterly earnings",
        ],
    ),
    "HR": DepartmentRoute(
        agent_name="HRRecruitmentAgent",
        display_name="People & Talent",
        keywords=[
            "payroll",
            "hiring",
            "recruit",
            "onboarding",
            "employee",
            "human resources",
            "compensation",
            "benefits",
            "performance review",
            "job posting",
            "candidate",
            "interview",
            "retention",
            "headcount",
            "salary",
            "leave",
            "pto",
            "training",
            "termination",
            "offboarding",
            "workforce",
            "talent",
            "staff",
            "personnel",
            "people ops",
        ],
    ),
    "MARKETING": DepartmentRoute(
        agent_name="MarketingAutomationAgent",
        display_name="Marketing & Growth",
        keywords=[
            "seo",
            "campaign",
            "marketing",
            "brand",
            "advertising",
            "ad spend",
            "lead generation",
            "content calendar",
            "social media",
            "email marketing",
            "newsletter",
            "ctr",
            "conversion rate",
            "landing page",
            "cpc",
            "impressions",
            "traffic",
            "google ads",
            "facebook ads",
            "influencer",
            "launch campaign",
            "promotion",
            "growth",
            "seo strategy",
            "marketing strategy",
        ],
    ),
    "SALES": DepartmentRoute(
        agent_name="SalesIntelligenceAgent",
        display_name="Sales & Revenue",
        keywords=[
            "deal",
            "pipeline",
            "prospect",
            "lead",
            "close the deal",
            "sales",
            "quota",
            "crm",
            "opportunity",
            "proposal",
            "outreach",
            "follow up",
            "demo",
            "negotiation",
            "contract",
            "win rate",
            "mrr",
            "arr",
            "churn",
            "upsell",
            "cross-sell",
            "account",
            "client acquisition",
            "cold email",
            "cold call",
        ],
    ),
    "OPERATIONS": DepartmentRoute(
        agent_name="OperationsOptimizationAgent",
        display_name="Operations & Processes",
        keywords=[
            "supply chain",
            "logistics",
            "operations",
            "process",
            "runbook",
            "sop",
            "standard operating procedure",
            "workflow",
            "inventory",
            "vendor",
            "procurement",
            "fulfillment",
            "capacity",
            "throughput",
            "bottleneck",
            "incident",
            "downtime",
            "infrastructure",
            "deployment",
            "release",
            "shipment",
            "warehouse",
            "optimize",
        ],
    ),
    "COMPLIANCE": DepartmentRoute(
        agent_name="ComplianceRiskAgent",
        display_name="Compliance & Risk",
        keywords=[
            "gdpr",
            "compliance",
            "regulation",
            "legal",
            "risk",
            "audit",
            "policy",
            "data protection",
            "privacy",
            "hipaa",
            "sox",
            "iso",
            "certification",
            "breach",
            "vulnerability",
            "security",
            "liability",
            "contract review",
            "regulatory",
            "governance",
            "data handling",
            "third-party risk",
        ],
    ),
    "CONTENT": DepartmentRoute(
        agent_name="ContentCreationAgent",
        display_name="Content & Creative",
        keywords=[
            "blog",
            "article",
            "copywriting",
            "content strategy",
            "video script",
            "podcast",
            "infographic",
            "design",
            "creative brief",
            "graphic",
            "visual",
            "thumbnail",
            "caption",
            "post",
            "write a",
            "draft a",
            "editorial",
        ],
    ),
    "STRATEGIC": DepartmentRoute(
        agent_name="StrategicPlanningAgent",
        display_name="Strategy & Planning",
        keywords=[
            "strategy",
            "roadmap",
            "okr",
            "objective",
            "key result",
            "initiative",
            "quarter plan",
            "annual plan",
            "competitive analysis",
            "market positioning",
            "business model",
            "expansion",
            "pivot",
            "vision",
            "mission",
            "swot",
            "strategic plan",
            "long-term",
            "north star",
        ],
    ),
    "SUPPORT": DepartmentRoute(
        agent_name="CustomerSupportAgent",
        display_name="Customer Success",
        keywords=[
            "customer support",
            "customer success",
            "ticket",
            "helpdesk",
            "support request",
            "customer complaint",
            "refund",
            "escalation",
            "resolution",
            "csat",
            "nps",
            "customer satisfaction",
            "issue report",
            "bug report",
            "sla breach",
            "response time",
        ],
    ),
    "DATA": DepartmentRoute(
        agent_name="DataAnalysisAgent",
        display_name="Data & Analytics",
        keywords=[
            "data analysis",
            "analytics",
            "dashboard",
            "report",
            "metrics",
            "kpi",
            "spreadsheet",
            "sql",
            "query",
            "dataset",
            "visualization",
            "chart",
            "trend",
            "cohort",
            "segmentation",
            "attribution",
            "data pipeline",
            "etl",
            "bi tool",
        ],
    ),
}


def _build_patterns() -> dict[str, list[tuple[re.Pattern[str], int]]]:
    """Pre-compile word-boundary regex patterns for each department.

    Returns a mapping from department type to list of (compiled_pattern, kw_len)
    tuples, sorted longest keyword first so more specific phrases match before
    shorter ones within the same department.
    """
    compiled: dict[str, list[tuple[re.Pattern[str], int]]] = {}
    for dept_type, route in DEPARTMENT_ROUTING.items():
        # Sort keywords by length descending so longer (more specific) phrases
        # are checked first.
        sorted_kws = sorted(route.keywords, key=len, reverse=True)
        compiled[dept_type] = [
            (re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE), len(kw))
            for kw in sorted_kws
        ]
    return compiled


_PATTERNS: dict[str, list[tuple[re.Pattern[str], int]]] = _build_patterns()


def detect_department(query: str) -> tuple[str, str] | None:
    """Detect the most relevant business department from a natural-language query.

    Matches are word-boundary aware to avoid false positives (e.g. "hr" inside
    "share" or "their").

    Args:
        query: A natural-language string from the user.

    Returns:
        A ``(department_type, agent_name)`` tuple when a department is detected,
        or ``None`` when no department keywords are found in the query.

    Examples:
        >>> detect_department("what's our payroll this month?")
        ('HR', 'HRRecruitmentAgent')
        >>> detect_department("tell me a joke")
        None
    """
    query_lower = query.lower()

    best_dept: str | None = None
    best_count: int = 0
    best_longest: int = 0  # length of the longest matched keyword (tie-breaker)

    for dept_type, patterns in _PATTERNS.items():
        count = 0
        longest = 0
        for pattern, kw_len in patterns:
            if pattern.search(query_lower):
                count += 1
                if kw_len > longest:
                    longest = kw_len

        if count == 0:
            continue

        # Prefer higher count; on tie prefer the longer (more specific) keyword
        if count > best_count or (count == best_count and longest > best_longest):
            best_count = count
            best_longest = longest
            best_dept = dept_type

    if best_dept is None:
        return None

    route = DEPARTMENT_ROUTING[best_dept]
    return (best_dept, route.agent_name)
