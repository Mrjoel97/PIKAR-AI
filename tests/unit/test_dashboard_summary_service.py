import pytest

from app.services.dashboard_summary_service import DashboardSummaryService


@pytest.mark.asyncio
async def test_get_home_summary_returns_persona_specific_founder_views():
    service = object.__new__(DashboardSummaryService)
    service._pending_approvals = lambda _user_id: []
    service._active_workflows = lambda _user_id: []
    service._recent_completed_workflows = lambda _user_id: []
    service._initiatives = lambda _user_id: []
    service._open_tasks = lambda _user_id: [{"id": "task-1", "title": "Email leads"}]
    service._brain_dumps = lambda _user_id: []
    service._content_queue = lambda _user_id: [{"id": "content-1", "title": "Launch post"}]
    service._reports = lambda _user_id: [{"id": "report-1", "title": "Weekly report"}]
    service._departments = lambda: []
    service._compliance_audits = lambda _user_id: []
    service._compliance_risks = lambda _user_id: []
    service._workflow_execution_audit = lambda _user_id: []
    service._workflow_template_audit = lambda _user_id: []
    service._financial_summary = lambda _user_id: {
        "currency": "USD",
        "revenue": 3200.0,
        "cash_position": 12000.0,
        "monthly_burn": 1800.0,
        "runway_months": 6.7,
    }

    solopreneur = await DashboardSummaryService.get_home_summary(service, user_id="u1", persona="solopreneur")
    startup = await DashboardSummaryService.get_home_summary(service, user_id="u1", persona="startup")

    assert [item["label"] for item in solopreneur["kpis"]] == [
        "Revenue this month",
        "Cash position",
        "Quick tasks",
        "Content queue",
    ]
    assert [item["label"] for item in startup["kpis"]] == [
        "Revenue this month",
        "Runway",
        "Active initiatives",
        "Pending approvals",
    ]
    assert solopreneur["recommended_action"]["href"] == "/dashboard/braindump"
    assert startup["recommended_action"]["href"] == "/dashboard/workflows/templates"
    assert solopreneur["headline"] != startup["headline"]


@pytest.mark.asyncio
async def test_get_home_summary_uses_persona_specific_governance_defaults():
    service = object.__new__(DashboardSummaryService)
    service._pending_approvals = lambda _user_id: []
    service._active_workflows = lambda _user_id: []
    service._recent_completed_workflows = lambda _user_id: []
    service._initiatives = lambda _user_id: []
    service._open_tasks = lambda _user_id: []
    service._brain_dumps = lambda _user_id: []
    service._content_queue = lambda _user_id: []
    service._reports = lambda _user_id: [{"id": "report-1", "title": "Board update"}]
    service._departments = lambda: [{"id": "dept-1", "title": "Operations", "status": "RUNNING"}]
    service._compliance_audits = lambda _user_id: [{"id": "audit-1", "title": "Quarterly compliance review", "status": "scheduled"}]
    service._compliance_risks = lambda _user_id: [{"id": "risk-1", "title": "Vendor access risk", "category": "high"}]
    service._workflow_execution_audit = lambda _user_id: [{"id": "evt-1", "title": "Board close", "category": "Approval Granted"}]
    service._workflow_template_audit = lambda _user_id: [{"id": "tmpl-1", "title": "Policy update", "category": "Publish"}]
    service._financial_summary = lambda _user_id: {
        "currency": "USD",
        "revenue": 0.0,
        "cash_position": 50000.0,
        "monthly_burn": 5000.0,
        "runway_months": 10.0,
    }

    sme = await DashboardSummaryService.get_home_summary(service, user_id="u1", persona="sme")
    enterprise = await DashboardSummaryService.get_home_summary(service, user_id="u1", persona="enterprise")

    assert sme["recommended_action"]["href"] == "/departments"
    assert enterprise["recommended_action"]["href"] == "/dashboard/workflows/active"
    assert [item["label"] for item in sme["kpis"]] == [
        "Departments running",
        "Open risks",
        "Pending approvals",
        "Recent reports",
    ]
    assert [item["label"] for item in enterprise["kpis"]] == [
        "Governance queue",
        "Execution audit",
        "Executive reports",
        "Open risks",
    ]
    assert sme["collections"]["departments"][0]["title"] == "Operations"
    assert enterprise["collections"]["execution_audit"][0]["title"] == "Board close"
