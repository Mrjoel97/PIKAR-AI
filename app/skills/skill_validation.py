"""Structured output validation for critical skill responses (Gap 1).

Provides Pydantic schemas for validating skill outputs and a validation
utility that can be applied to any skill's use_skill response.
"""

import logging
from typing import Any
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


# ─── Pydantic schemas for critical skill outputs ───

class FinancialAnalysisOutput(BaseModel):
    """Expected structure for financial analysis skill outputs."""
    revenue: float | None = Field(default=None, description="Revenue figure")
    expenses: float | None = Field(default=None, description="Expenses figure")
    net_income: float | None = Field(default=None, description="Net income")
    margin_pct: float | None = Field(default=None, description="Profit margin %")
    period: str | None = Field(default=None, description="Analysis period")
    insights: list[str] = Field(default_factory=list, description="Key insights")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations")


class CompetitiveAnalysisOutput(BaseModel):
    """Expected structure for competitive analysis outputs."""
    competitors: list[str] = Field(default_factory=list, description="Identified competitors")
    strengths: list[str] = Field(default_factory=list, description="Own strengths")
    weaknesses: list[str] = Field(default_factory=list, description="Own weaknesses")
    opportunities: list[str] = Field(default_factory=list, description="Market opportunities")
    threats: list[str] = Field(default_factory=list, description="Market threats")
    recommendation: str | None = Field(default=None, description="Strategic recommendation")


class RiskAssessmentOutput(BaseModel):
    """Expected structure for risk assessment outputs."""
    risk_level: str | None = Field(default=None, description="Overall risk level")
    risks: list[dict] = Field(default_factory=list, description="Identified risks")
    mitigations: list[str] = Field(default_factory=list, description="Mitigation strategies")
    compliance_status: str | None = Field(default=None, description="Compliance status")


class CampaignIdeationOutput(BaseModel):
    """Expected structure for campaign ideation outputs."""
    campaign_name: str | None = Field(default=None, description="Proposed name")
    target_audience: str | None = Field(default=None, description="Target audience")
    channels: list[str] = Field(default_factory=list, description="Marketing channels")
    key_messages: list[str] = Field(default_factory=list, description="Key messages")
    budget_range: str | None = Field(default=None, description="Estimated budget")
    timeline: str | None = Field(default=None, description="Campaign timeline")


# ─── Skill → Schema mapping ───

SKILL_SCHEMAS: dict[str, type[BaseModel]] = {
    "analyze_financial_statement": FinancialAnalysisOutput,
    "forecast_revenue_growth": FinancialAnalysisOutput,
    "calculate_burn_rate": FinancialAnalysisOutput,
    "competitive_analysis": CompetitiveAnalysisOutput,
    "risk_assessment_matrix": RiskAssessmentOutput,
    "gdpr_audit_checklist": RiskAssessmentOutput,
    "campaign_ideation": CampaignIdeationOutput,
}


def validate_skill_output(skill_name: str, output: Any) -> dict[str, Any]:
    """Validate a skill's output against its registered Pydantic schema.

    Args:
        skill_name: The skill that produced the output.
        output: The raw output dict from the skill.

    Returns:
        Dict with 'valid' (bool), 'validated' (parsed model dict or None),
        and 'errors' (list of validation error messages or empty).
    """
    schema = SKILL_SCHEMAS.get(skill_name)

    if not schema:
        # No schema registered — pass through
        return {"valid": True, "validated": output, "errors": []}

    if not isinstance(output, dict):
        return {
            "valid": False,
            "validated": None,
            "errors": [f"Expected dict output, got {type(output).__name__}"],
        }

    try:
        model = schema.model_validate(output)
        return {"valid": True, "validated": model.model_dump(), "errors": []}
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        logger.warning(
            "Skill '%s' output validation failed: %s", skill_name, errors
        )
        # Return the original output with validation warnings
        return {"valid": False, "validated": output, "errors": errors}
