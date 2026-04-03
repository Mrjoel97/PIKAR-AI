"""Tests for department routing configuration and detect_department function."""

from __future__ import annotations


def test_department_routing_has_all_required_keys():
    """DEPARTMENT_ROUTING contains all 10 expected department types."""
    from app.config.department_routing import DEPARTMENT_ROUTING

    expected_keys = {
        "FINANCIAL",
        "OPERATIONS",
        "MARKETING",
        "SALES",
        "HR",
        "COMPLIANCE",
        "CONTENT",
        "STRATEGIC",
        "SUPPORT",
        "DATA",
    }
    assert set(DEPARTMENT_ROUTING.keys()) == expected_keys


def test_department_routing_entries_have_required_fields():
    """Each DepartmentRoute has agent_name, display_name, and keywords."""
    from app.config.department_routing import DEPARTMENT_ROUTING

    for dept_type, route in DEPARTMENT_ROUTING.items():
        assert hasattr(route, "agent_name"), f"{dept_type} missing agent_name"
        assert hasattr(route, "display_name"), f"{dept_type} missing display_name"
        assert hasattr(route, "keywords"), f"{dept_type} missing keywords"
        assert isinstance(route.agent_name, str), f"{dept_type}.agent_name is not str"
        assert isinstance(route.display_name, str), f"{dept_type}.display_name is not str"
        assert isinstance(route.keywords, list), f"{dept_type}.keywords is not list"
        assert len(route.keywords) > 0, f"{dept_type} has empty keywords list"


def test_detect_department_hr_payroll_question():
    """Payroll question maps to HR -> HRRecruitmentAgent."""
    from app.config.department_routing import detect_department

    result = detect_department("what's our payroll this month?")
    assert result is not None
    dept_type, agent_name = result
    assert dept_type == "HR"
    assert agent_name == "HRRecruitmentAgent"


def test_detect_department_financial_revenue_forecast():
    """Revenue forecast question maps to FINANCIAL -> FinancialAnalysisAgent."""
    from app.config.department_routing import detect_department

    result = detect_department("revenue forecast for Q3")
    assert result is not None
    dept_type, agent_name = result
    assert dept_type == "FINANCIAL"
    assert agent_name == "FinancialAnalysisAgent"


def test_detect_department_marketing_seo():
    """SEO strategy question maps to MARKETING -> MarketingAutomationAgent."""
    from app.config.department_routing import detect_department

    result = detect_department("update our SEO strategy")
    assert result is not None
    dept_type, agent_name = result
    assert dept_type == "MARKETING"
    assert agent_name == "MarketingAutomationAgent"


def test_detect_department_operations_supply_chain():
    """Supply chain question maps to OPERATIONS -> OperationsOptimizationAgent."""
    from app.config.department_routing import detect_department

    result = detect_department("optimize our supply chain")
    assert result is not None
    dept_type, agent_name = result
    assert dept_type == "OPERATIONS"
    assert agent_name == "OperationsOptimizationAgent"


def test_detect_department_compliance_gdpr():
    """GDPR compliance question maps to COMPLIANCE -> ComplianceRiskAgent."""
    from app.config.department_routing import detect_department

    result = detect_department("check GDPR compliance status")
    assert result is not None
    dept_type, agent_name = result
    assert dept_type == "COMPLIANCE"
    assert agent_name == "ComplianceRiskAgent"


def test_detect_department_sales_deal():
    """Deal closing question maps to SALES -> SalesIntelligenceAgent."""
    from app.config.department_routing import detect_department

    result = detect_department("close the deal with Acme Corp")
    assert result is not None
    dept_type, agent_name = result
    assert dept_type == "SALES"
    assert agent_name == "SalesIntelligenceAgent"


def test_detect_department_generic_joke_returns_none():
    """Generic non-business question returns None."""
    from app.config.department_routing import detect_department

    result = detect_department("tell me a joke")
    assert result is None


def test_detect_department_generic_business_returns_none():
    """Vague generic business question returns None (no specific department)."""
    from app.config.department_routing import detect_department

    result = detect_department("how is the business doing?")
    assert result is None


def test_detect_department_returns_tuple_format():
    """detect_department returns a tuple of (str, str) when matched."""
    from app.config.department_routing import detect_department

    result = detect_department("what is our burn rate?")
    assert result is not None
    assert isinstance(result, tuple)
    assert len(result) == 2
    dept_type, agent_name = result
    assert isinstance(dept_type, str)
    assert isinstance(agent_name, str)


def test_detect_department_case_insensitive():
    """Query matching is case-insensitive."""
    from app.config.department_routing import detect_department

    result_lower = detect_department("what is our payroll budget?")
    result_upper = detect_department("WHAT IS OUR PAYROLL BUDGET?")
    assert result_lower is not None
    assert result_upper is not None
    assert result_lower == result_upper


def test_detect_department_hr_partial_word_no_false_positive():
    """'hr' keyword should not match inside 'share' or 'their'."""
    from app.config.department_routing import detect_department

    # These contain 'hr' as substring but not as a word - should NOT route to HR
    result = detect_department("share their strategy document")
    # The result could be None or match something else, but must NOT be HR
    if result is not None:
        dept_type, _ = result
        assert dept_type != "HR", (
            "Partial word match 'share/their' incorrectly matched HR keyword 'hr'"
        )


def test_detect_department_hr_hiring_question():
    """Hiring question maps to HR."""
    from app.config.department_routing import detect_department

    result = detect_department("we need to recruit a senior engineer")
    assert result is not None
    dept_type, agent_name = result
    assert dept_type == "HR"
    assert agent_name == "HRRecruitmentAgent"


def test_detect_department_financial_budget():
    """Budget question maps to FINANCIAL."""
    from app.config.department_routing import detect_department

    result = detect_department("what is our Q4 budget allocation?")
    assert result is not None
    dept_type, agent_name = result
    assert dept_type == "FINANCIAL"
    assert agent_name == "FinancialAnalysisAgent"


def test_detect_department_sales_pipeline():
    """Sales pipeline question maps to SALES."""
    from app.config.department_routing import detect_department

    result = detect_department("show me the sales pipeline")
    assert result is not None
    dept_type, agent_name = result
    assert dept_type == "SALES"
    assert agent_name == "SalesIntelligenceAgent"


def test_department_routing_financial_agent_name():
    """FINANCIAL entry has correct agent name."""
    from app.config.department_routing import DEPARTMENT_ROUTING

    assert DEPARTMENT_ROUTING["FINANCIAL"].agent_name == "FinancialAnalysisAgent"


def test_department_routing_hr_agent_name():
    """HR entry has correct agent name."""
    from app.config.department_routing import DEPARTMENT_ROUTING

    assert DEPARTMENT_ROUTING["HR"].agent_name == "HRRecruitmentAgent"


def test_department_routing_marketing_agent_name():
    """MARKETING entry has correct agent name."""
    from app.config.department_routing import DEPARTMENT_ROUTING

    assert DEPARTMENT_ROUTING["MARKETING"].agent_name == "MarketingAutomationAgent"


def test_department_routing_sales_agent_name():
    """SALES entry has correct agent name."""
    from app.config.department_routing import DEPARTMENT_ROUTING

    assert DEPARTMENT_ROUTING["SALES"].agent_name == "SalesIntelligenceAgent"


def test_department_routing_operations_agent_name():
    """OPERATIONS entry has correct agent name."""
    from app.config.department_routing import DEPARTMENT_ROUTING

    assert DEPARTMENT_ROUTING["OPERATIONS"].agent_name == "OperationsOptimizationAgent"


def test_department_routing_compliance_agent_name():
    """COMPLIANCE entry has correct agent name."""
    from app.config.department_routing import DEPARTMENT_ROUTING

    assert DEPARTMENT_ROUTING["COMPLIANCE"].agent_name == "ComplianceRiskAgent"
