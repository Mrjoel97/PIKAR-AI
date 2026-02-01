# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for agent output schemas and report sub-agents.

Tests that:
1. All Pydantic schemas are importable and valid
2. Report agents have output_schema and output_key set (if reportlab available)
3. Parent agents have report agents in sub_agents (if reportlab available)
4. Report agents do NOT have tools assigned (if reportlab available)
"""

import pytest
from datetime import date

# Check if reportlab is available (required for agent imports)
try:
    import reportlab
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


class TestPydanticSchemas:
    """Tests for Pydantic output schemas.
    
    These tests only import the schemas module which has no external dependencies.
    """

    def test_financial_report_schema_valid(self):
        """Test FinancialReport schema can be instantiated."""
        from app.agents.schemas import FinancialReport, MonthlyRevenue, ExpenseCategory

        report = FinancialReport(
            report_date=date.today(),
            period="Q4 2025",
            summary="Strong quarter with revenue growth.",
            revenue=125000.0,
            expenses=87000.0,
            net_income=38000.0,
            profit_margin=30.4,
            trend="growing",
            recommendations=["Invest in marketing", "Reduce vendor costs"],
            revenue_by_month=[
                MonthlyRevenue(month="October 2025", revenue=40000, expenses=28000),
                MonthlyRevenue(month="November 2025", revenue=42000, expenses=29000),
            ],
            expense_categories=[
                ExpenseCategory(category="Payroll", amount=50000, percentage=57.5),
            ],
        )
        assert report.profit_margin == 30.4
        assert report.trend == "growing"

    def test_lead_qualification_schema_valid(self):
        """Test LeadQualification schema can be instantiated."""
        from app.agents.schemas import LeadQualification, CriteriaScore

        lead = LeadQualification(
            lead_name="John Smith",
            company="Acme Corp",
            industry="Technology",
            score=85,
            framework="BANT",
            qualified=True,
            priority="high",
            next_steps=["Schedule discovery call", "Send case study"],
            criteria_breakdown=[
                CriteriaScore(criterion="Budget", score=90, notes="$50K confirmed"),
            ],
        )
        assert lead.score == 85
        assert lead.qualified is True

    def test_risk_assessment_schema_valid(self):
        """Test RiskAssessment schema can be instantiated."""
        from app.agents.schemas import RiskAssessment

        risk = RiskAssessment(
            risk_id="RISK-001",
            title="GDPR Compliance Gap",
            description="Missing data processing agreements with vendors.",
            category="legal",
            severity="high",
            probability="likely",
            impact_score=16,
            mitigation="Implement DPAs with all vendors.",
            owner="Data Protection Officer",
            due_date=date(2025, 3, 15),
            status="identified",
        )
        assert risk.impact_score == 16
        assert risk.severity == "high"

    def test_data_insight_schema_valid(self):
        """Test DataInsight schema can be instantiated."""
        from app.agents.schemas import DataInsight, TimeSeriesPoint

        insight = DataInsight(
            metric_name="Monthly Active Users",
            current_value=14200,
            previous_value=12500,
            change_percent=13.6,
            change_direction="up",
            anomaly_detected=False,
            anomaly_severity="none",
            insight="Growth consistent with marketing campaigns.",
            recommendation="Continue current acquisition strategy.",
            time_series=[
                TimeSeriesPoint(timestamp="2025-01-01", value=12500),
                TimeSeriesPoint(timestamp="2025-02-01", value=14200),
            ],
        )
        assert insight.change_percent == 13.6
        assert insight.anomaly_detected is False

    def test_all_schemas_exportable(self):
        """Test that all schemas are exported in __all__."""
        # Import directly to avoid triggering app.agents.__init__ circular imports
        import app.agents.schemas as schemas
        
        expected_exports = [
            "MonthlyRevenue",
            "ExpenseCategory",
            "FinancialReport",
            "CriteriaScore",
            "LeadQualification",
            "RiskAssessment",
            "TimeSeriesPoint",
            "DataInsight",
        ]
        for export in expected_exports:
            assert export in schemas.__all__, f"{export} not in __all__"


@pytest.mark.skipif(not HAS_REPORTLAB, reason="reportlab required for agent imports")
class TestReportSubAgents:
    """Tests for report sub-agent configuration."""

    def test_financial_report_agent_has_output_schema(self):
        """Test FinancialReportAgent has output_schema configured."""
        from app.agents.financial.agent import financial_report_agent
        from app.agents.schemas import FinancialReport

        assert financial_report_agent.output_schema == FinancialReport
        assert financial_report_agent.output_key == "financial_report"

    def test_lead_scoring_agent_has_output_schema(self):
        """Test LeadScoringAgent has output_schema configured."""
        from app.agents.sales.agent import lead_scoring_agent
        from app.agents.schemas import LeadQualification

        assert lead_scoring_agent.output_schema == LeadQualification
        assert lead_scoring_agent.output_key == "lead_qualification"

    def test_risk_report_agent_has_output_schema(self):
        """Test RiskReportAgent has output_schema configured."""
        from app.agents.compliance.agent import risk_report_agent
        from app.agents.schemas import RiskAssessment

        assert risk_report_agent.output_schema == RiskAssessment
        assert risk_report_agent.output_key == "risk_assessment"

    def test_data_insight_agent_has_output_schema(self):
        """Test DataInsightAgent has output_schema configured."""
        from app.agents.data.agent import data_insight_agent
        from app.agents.schemas import DataInsight

        assert data_insight_agent.output_schema == DataInsight
        assert data_insight_agent.output_key == "data_insight"


@pytest.mark.skipif(not HAS_REPORTLAB, reason="reportlab required for agent imports")
class TestParentAgentSubAgents:
    """Tests for parent agent sub_agents configuration."""

    def test_financial_agent_has_report_subagent(self):
        """Test FinancialAnalysisAgent includes FinancialReportAgent as sub-agent."""
        from app.agents.financial.agent import financial_agent, financial_report_agent

        assert financial_report_agent in financial_agent.sub_agents

    def test_sales_agent_has_scoring_subagent(self):
        """Test SalesIntelligenceAgent includes LeadScoringAgent as sub-agent."""
        from app.agents.sales.agent import sales_agent, lead_scoring_agent

        assert lead_scoring_agent in sales_agent.sub_agents

    def test_compliance_agent_has_risk_subagent(self):
        """Test ComplianceRiskAgent includes RiskReportAgent as sub-agent."""
        from app.agents.compliance.agent import compliance_agent, risk_report_agent

        assert risk_report_agent in compliance_agent.sub_agents

    def test_data_agent_has_insight_subagent(self):
        """Test DataAnalysisAgent includes DataInsightAgent as sub-agent."""
        from app.agents.data.agent import data_agent, data_insight_agent

        assert data_insight_agent in data_agent.sub_agents


@pytest.mark.skipif(not HAS_REPORTLAB, reason="reportlab required for agent imports")
class TestReportAgentsNoTools:
    """Tests that report agents do not have tools (validates trade-off)."""

    def test_financial_report_agent_no_tools(self):
        """Report agents with output_schema should not have tools."""
        from app.agents.financial.agent import financial_report_agent

        assert not financial_report_agent.tools or len(financial_report_agent.tools) == 0

    def test_lead_scoring_agent_no_tools(self):
        """Report agents with output_schema should not have tools."""
        from app.agents.sales.agent import lead_scoring_agent

        assert not lead_scoring_agent.tools or len(lead_scoring_agent.tools) == 0

    def test_risk_report_agent_no_tools(self):
        """Report agents with output_schema should not have tools."""
        from app.agents.compliance.agent import risk_report_agent

        assert not risk_report_agent.tools or len(risk_report_agent.tools) == 0

    def test_data_insight_agent_no_tools(self):
        """Report agents with output_schema should not have tools."""
        from app.agents.data.agent import data_insight_agent

        assert not data_insight_agent.tools or len(data_insight_agent.tools) == 0


