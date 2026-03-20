# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pydantic output schemas for structured agent responses.

These schemas enable agents to produce predictable JSON output that can be:
1. Narrated by parent agents into natural language
2. Embedded in responses via <json>...</json> blocks for frontend rendering
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# Financial Schemas
# =============================================================================


class MonthlyRevenue(BaseModel):
    """Monthly revenue data point for chart rendering."""

    month: str = Field(description="Month name e.g. 'January 2025'")
    revenue: float = Field(description="Revenue amount in USD")
    expenses: float = Field(description="Expenses amount in USD")


class ExpenseCategory(BaseModel):
    """Expense breakdown for pie chart rendering."""

    category: str = Field(description="Expense category name")
    amount: float = Field(description="Amount in USD")
    percentage: float = Field(description="Percentage of total expenses")


class FinancialReport(BaseModel):
    """Structured output for financial analysis.

    Used by FinancialReportAgent to produce JSON that the parent
    FinancialAnalysisAgent narrates for users.
    """

    report_date: date
    period: str = Field(description="Reporting period e.g. 'Q4 2025'")
    summary: str = Field(description="Executive summary of financial health")
    revenue: float = Field(description="Total revenue in USD")
    expenses: float = Field(description="Total expenses in USD")
    net_income: float = Field(description="Net income (revenue - expenses)")
    profit_margin: float = Field(description="Profit margin percentage")
    trend: Literal["growing", "stable", "declining"]
    recommendations: list[str] = Field(description="Action items")
    # For chart rendering
    revenue_by_month: list[MonthlyRevenue] = Field(
        default_factory=list, description="Monthly breakdown for trend charts"
    )
    expense_categories: list[ExpenseCategory] = Field(
        default_factory=list, description="Expense breakdown for pie charts"
    )


# =============================================================================
# Sales Schemas
# =============================================================================


class CriteriaScore(BaseModel):
    """Individual criterion score for lead qualification."""

    criterion: str = Field(description="Criterion name e.g. 'Budget'")
    score: int = Field(ge=0, le=100, description="Score for this criterion")
    notes: str = Field(description="Details supporting the score")


class LeadQualification(BaseModel):
    """Structured output for lead scoring.

    Used by LeadScoringAgent to produce JSON that the parent
    SalesIntelligenceAgent narrates for users.
    """

    lead_name: str
    company: str
    industry: str | None = None
    score: int = Field(ge=0, le=100, description="Overall lead score 0-100")
    framework: Literal["BANT", "MEDDIC", "CHAMP"]
    qualified: bool
    priority: Literal["low", "medium", "high", "urgent"]
    next_steps: list[str]
    criteria_breakdown: list[CriteriaScore] = Field(
        default_factory=list, description="Score breakdown for visualization"
    )


# =============================================================================
# Compliance Schemas
# =============================================================================


class RiskAssessment(BaseModel):
    """Structured output for compliance risk evaluation.

    Used by RiskReportAgent to produce JSON that the parent
    ComplianceRiskAgent narrates for users.
    """

    risk_id: str
    title: str
    description: str
    category: Literal["legal", "financial", "operational", "reputational"]
    severity: Literal["low", "medium", "high", "critical"]
    probability: Literal["unlikely", "possible", "likely", "certain"]
    impact_score: int = Field(
        ge=1, le=25, description="Risk matrix score (severity * probability)"
    )
    mitigation: str = Field(description="Recommended mitigation strategy")
    owner: str = Field(description="Responsible party for addressing this risk")
    due_date: date | None = None
    status: Literal["identified", "in_progress", "mitigated", "accepted"] = "identified"


# =============================================================================
# Data Analysis Schemas
# =============================================================================


class TimeSeriesPoint(BaseModel):
    """Single data point in a time series."""

    timestamp: str = Field(description="ISO format timestamp or date string")
    value: float


class DataInsight(BaseModel):
    """Structured output for data analysis findings.

    Used by DataInsightAgent to produce JSON that the parent
    DataAnalysisAgent narrates for users.
    """

    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    change_direction: Literal["up", "down", "stable"]
    anomaly_detected: bool
    anomaly_severity: Literal["none", "minor", "moderate", "severe"] = "none"
    insight: str = Field(description="Human-readable interpretation of the data")
    recommendation: str | None = None
    time_series: list[TimeSeriesPoint] = Field(
        default_factory=list, description="Historical data for trend charts"
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Financial
    "MonthlyRevenue",
    "ExpenseCategory",
    "FinancialReport",
    # Sales
    "CriteriaScore",
    "LeadQualification",
    # Compliance
    "RiskAssessment",
    # Data
    "TimeSeriesPoint",
    "DataInsight",
]
