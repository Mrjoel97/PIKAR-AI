import pytest

from app.services.dashboard_summary_service import DashboardSummaryService


async def _empty_list(_user_id=""):
    return []


async def _empty_dict(_user_id=""):
    return {}


@pytest.mark.asyncio
async def test_get_home_summary_returns_persona_specific_founder_views():
    service = object.__new__(DashboardSummaryService)

    async def _pending_approvals(_user_id):
        return []

    async def _active_workflows(_user_id):
        return []

    async def _recent_completed_workflows(_user_id):
        return []

    async def _initiatives(_user_id):
        return []

    async def _open_tasks(_user_id):
        return [{"id": "task-1", "title": "Email leads"}]

    async def _brain_dumps(_user_id):
        return []

    async def _content_queue(_user_id):
        return [{"id": "content-1", "title": "Launch post"}]

    async def _reports(_user_id):
        return [{"id": "report-1", "title": "Weekly report"}]

    async def _departments():
        return []

    async def _compliance_audits(_user_id):
        return []

    async def _compliance_risks(_user_id):
        return []

    async def _workflow_execution_audit(_user_id):
        return []

    async def _workflow_template_audit(_user_id):
        return []

    async def _financial_summary(_user_id):
        return {
            "currency": "USD",
            "revenue": 3200.0,
            "cash_position": 12000.0,
            "monthly_burn": 1800.0,
            "runway_months": 6.7,
        }

    service._pending_approvals = _pending_approvals
    service._active_workflows = _active_workflows
    service._recent_completed_workflows = _recent_completed_workflows
    service._initiatives = _initiatives
    service._open_tasks = _open_tasks
    service._brain_dumps = _brain_dumps
    service._content_queue = _content_queue
    service._reports = _reports
    service._departments = _departments
    service._compliance_audits = _compliance_audits
    service._compliance_risks = _compliance_risks
    service._workflow_execution_audit = _workflow_execution_audit
    service._workflow_template_audit = _workflow_template_audit
    service._financial_summary = _financial_summary

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

    async def _pending_approvals(_user_id):
        return []

    async def _active_workflows(_user_id):
        return []

    async def _recent_completed_workflows(_user_id):
        return []

    async def _initiatives(_user_id):
        return []

    async def _open_tasks(_user_id):
        return []

    async def _brain_dumps(_user_id):
        return []

    async def _content_queue(_user_id):
        return []

    async def _reports(_user_id):
        return [{"id": "report-1", "title": "Board update"}]

    async def _departments():
        return [{"id": "dept-1", "title": "Operations", "status": "RUNNING"}]

    async def _compliance_audits(_user_id):
        return [{"id": "audit-1", "title": "Quarterly compliance review", "status": "scheduled"}]

    async def _compliance_risks(_user_id):
        return [{"id": "risk-1", "title": "Vendor access risk", "category": "high"}]

    async def _workflow_execution_audit(_user_id):
        return [{"id": "evt-1", "title": "Board close", "category": "Approval Granted"}]

    async def _workflow_template_audit(_user_id):
        return [{"id": "tmpl-1", "title": "Policy update", "category": "Publish"}]

    async def _financial_summary(_user_id):
        return {
            "currency": "USD",
            "revenue": 0.0,
            "cash_position": 50000.0,
            "monthly_burn": 5000.0,
            "runway_months": 10.0,
        }

    service._pending_approvals = _pending_approvals
    service._active_workflows = _active_workflows
    service._recent_completed_workflows = _recent_completed_workflows
    service._initiatives = _initiatives
    service._open_tasks = _open_tasks
    service._brain_dumps = _brain_dumps
    service._content_queue = _content_queue
    service._reports = _reports
    service._departments = _departments
    service._compliance_audits = _compliance_audits
    service._compliance_risks = _compliance_risks
    service._workflow_execution_audit = _workflow_execution_audit
    service._workflow_template_audit = _workflow_template_audit
    service._financial_summary = _financial_summary

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
