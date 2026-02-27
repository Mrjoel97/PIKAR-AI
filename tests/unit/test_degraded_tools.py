import pytest

from app.agents.tools import degraded_tools


@pytest.fixture(autouse=True)
def _patch_dependencies(monkeypatch):
    async def _fake_create_task(description: str):
        return {"success": True, "task": {"id": "task-1", "description": description}}

    async def _fake_save_content(title: str, content: str):
        return {"success": True, "content": {"id": "content-1", "title": title, "content": content}}

    async def _fake_track_event(event_name: str, category: str, properties: str = None):
        return {"success": True, "event": {"name": event_name, "category": category, "properties": properties}}

    async def _fake_create_campaign(name: str, campaign_type: str, target_audience: str):
        return {"success": True, "campaign": {"id": "camp-1", "name": name, "type": campaign_type, "target": target_audience}}

    async def _fake_create_initiative(title: str, description: str, priority: str = "medium"):
        return {"success": True, "initiative": {"id": "init-1", "title": title, "description": description, "priority": priority}}

    async def _fake_query_events(event_name: str = None, category: str = None, limit: int = 100):
        return {"success": True, "events": [{"id": "evt-1", "name": event_name, "category": category}], "count": 1}

    async def _fake_create_report(title: str, report_type: str, data: str, description: str = None):
        return {"success": True, "report": {"id": "rep-1", "title": title, "type": report_type, "description": description}}

    async def _fake_create_audit(title: str, scope: str, auditor: str, scheduled_date: str):
        return {"success": True, "audit": {"id": "audit-1", "title": title, "scope": scope, "auditor": auditor}}

    async def _fake_quick_research(topic: str, user_id: str = None):
        return {"success": True, "summary": f"researched {topic}", "user_id": user_id}

    monkeypatch.setattr(degraded_tools, "create_task", _fake_create_task)
    monkeypatch.setattr(degraded_tools, "save_content", _fake_save_content)
    monkeypatch.setattr(degraded_tools, "track_event", _fake_track_event)
    monkeypatch.setattr(degraded_tools, "create_campaign", _fake_create_campaign)
    monkeypatch.setattr(degraded_tools, "create_initiative", _fake_create_initiative)
    monkeypatch.setattr(degraded_tools, "query_events", _fake_query_events)
    monkeypatch.setattr(degraded_tools, "create_report", _fake_create_report)
    monkeypatch.setattr(degraded_tools, "create_audit", _fake_create_audit)
    monkeypatch.setattr(degraded_tools, "quick_research", _fake_quick_research)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_fn", "kwargs"),
    [
        (degraded_tools.create_folder, {"name": "Ops"}),
        (degraded_tools.create_project, {"name": "Project X"}),
        (degraded_tools.analyze_sentiment, {"query": "customer reviews"}),
        (degraded_tools.setup_monitoring, {"description": "uptime alerts"}),
        (degraded_tools.configure_ads, {"name": "Q2 Ads", "target_audience": "founders"}),
        (degraded_tools.optimize_spend, {"name": "Budget Runway"}),
        (degraded_tools.create_contact, {"name": "Alice", "email": "alice@example.com"}),
        (degraded_tools.score_lead, {"lead_name": "Lead A", "score": 82}),
        (degraded_tools.query_crm, {"limit": 10}),
        (degraded_tools.generate_forecast, {"title": "Revenue"}),
        (degraded_tools.create_forecast, {"title": "Cashflow"}),
        (degraded_tools.create_vendor, {"name": "Vendor A"}),
        (degraded_tools.update_inventory, {"item": "SKU-1", "quantity": 3}),
        (degraded_tools.create_po, {"vendor": "Vendor A", "amount": 100.0}),
        (degraded_tools.log_shipment, {"reference": "SHP-1"}),
        (degraded_tools.verify_po, {"reference": "PO-1"}),
        (degraded_tools.book_travel, {"traveler": "Alice", "itinerary": "NYC"}),
        (degraded_tools.process_expense, {"expense_title": "Flight", "amount": 450.0}),
        (degraded_tools.assign_training, {"training_name": "SOC2", "assignee": "Ops"}),
        (degraded_tools.post_job_board, {"role": "Engineer"}),
        (degraded_tools.query_analytics, {"event_name": "page_view", "limit": 5}),
        (degraded_tools.query_usage, {"event_name": "active_user", "limit": 5}),
        (degraded_tools.create_alert, {"message": "Threshold exceeded", "severity": "high"}),
        (degraded_tools.update_subscription, {"plan": "pro", "status": "active"}),
        (degraded_tools.upload_document, {"name": "spec.pdf"}),
        (degraded_tools.upload_file, {"name": "brief.txt"}),
        (degraded_tools.ocr_document, {"name": "scan.png"}),
        (degraded_tools.run_audit, {"title": "Ops Audit", "scope": "operations"}),
        (degraded_tools.run_test, {"name": "Regression"}),
        (degraded_tools.test_scenario, {"name": "Checkout flow"}),
        (degraded_tools.create_checklist, {"name": "Launch checklist"}),
        (degraded_tools.run_checklist, {"name": "Launch checklist"}),
        (degraded_tools.create_task_list, {"name": "Sprint backlog"}),
        (degraded_tools.record_notes, {"title": "Meeting notes"}),
    ],
)
async def test_tier_a_degraded_tools_produce_artifacts(tool_fn, kwargs):
    result = await tool_fn(**kwargs)
    assert result.get("success") is True
    assert result.get("status") == "degraded_completed"
    assert result.get("tool")
    assert result.get("status") != "simulated_success"
