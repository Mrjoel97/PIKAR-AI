"""Tests for UI widget tools (app/agents/tools/ui_widgets.py).

Validates that each widget-creation tool returns well-formed widget
definitions with the correct type, required fields, and data processing.
"""

import json
import pytest

from app.agents.tools.ui_widgets import (
    create_initiative_dashboard_widget,
    create_revenue_chart_widget,
    create_product_launch_widget,
    create_kanban_board_widget,
    create_workflow_builder_widget,
    create_morning_briefing_widget,
    create_boardroom_widget,
    create_suggested_workflows_widget,
    create_form_widget,
    create_table_widget,
    create_calendar_widget,
    create_campaign_hub_widget,
    display_workflow,
    display_workflow_observability,
    display_workflow_timeline,
    _parse_json_param,
)


# =============================================================================
# _parse_json_param helper
# =============================================================================

class TestParseJsonParam:
    """Tests for the JSON-string parameter parser."""

    def test_parses_valid_json_string(self):
        result = _parse_json_param('[{"a": 1}]', "test")
        assert result == [{"a": 1}]

    def test_returns_value_if_already_parsed(self):
        data = [{"a": 1}]
        result = _parse_json_param(data, "test")
        assert result is data

    def test_returns_empty_list_on_invalid_json(self):
        result = _parse_json_param("not json at all", "test")
        assert result == []

    def test_handles_dict_passthrough(self):
        d = {"key": "val"}
        assert _parse_json_param(d, "test") is d


# =============================================================================
# display_workflow
# =============================================================================

class TestDisplayWorkflow:
    def test_returns_workflow_widget_definition(self):
        result = display_workflow(execution_id="exec-123")
        assert result["type"] == "workflow"
        assert result["title"] == "Workflow Status"
        assert result["data"]["execution_id"] == "exec-123"

    def test_includes_dismissible_flag(self):
        result = display_workflow(execution_id="exec-abc")
        assert result["dismissible"] is True

    def test_includes_expandable_flag(self):
        result = display_workflow(execution_id="exec-abc")
        assert result["expandable"] is True


# =============================================================================
# create_initiative_dashboard_widget
# =============================================================================

class TestCreateInitiativeDashboardWidget:
    def test_returns_initiative_dashboard_type(self):
        result = create_initiative_dashboard_widget(initiatives="[]")
        assert result["type"] == "initiative_dashboard"
        assert result["title"] == "Strategic Initiatives"

    def test_processes_initiatives_from_json_string(self):
        initiatives_json = json.dumps([
            {"name": "Q1 Launch", "status": "in_progress", "progress": 60, "owner": "Alice"},
            {"name": "Q2 Expansion", "status": "completed", "progress": 100, "owner": "Bob"},
        ])
        result = create_initiative_dashboard_widget(initiatives=initiatives_json)
        data = result["data"]
        assert len(data["initiatives"]) == 2
        assert data["initiatives"][0]["name"] == "Q1 Launch"
        assert data["initiatives"][0]["owner"] == "Alice"
        assert data["initiatives"][1]["status"] == "completed"

    def test_computes_metrics(self):
        initiatives_json = json.dumps([
            {"name": "A", "status": "completed"},
            {"name": "B", "status": "in_progress"},
            {"name": "C", "status": "blocked"},
            {"name": "D", "status": "not_started"},
        ])
        result = create_initiative_dashboard_widget(initiatives=initiatives_json)
        metrics = result["data"]["metrics"]
        assert metrics["total"] == 4
        assert metrics["completed"] == 1
        assert metrics["in_progress"] == 1
        assert metrics["blocked"] == 1

    def test_includes_dismissible_and_expandable(self):
        result = create_initiative_dashboard_widget(initiatives="[]")
        assert result["dismissible"] is True
        assert result["expandable"] is True

    def test_generates_id_when_missing(self):
        initiatives_json = json.dumps([{"name": "No ID"}])
        result = create_initiative_dashboard_widget(initiatives=initiatives_json)
        init = result["data"]["initiatives"][0]
        assert init["id"].startswith("init-")


# =============================================================================
# create_revenue_chart_widget
# =============================================================================

class TestCreateRevenueChartWidget:
    def test_returns_revenue_chart_type(self):
        result = create_revenue_chart_widget(periods=["Jan", "Feb"], values=[100.0, 120.0])
        assert result["type"] == "revenue_chart"
        assert result["title"] == "Revenue Overview"

    def test_computes_current_period_stats(self):
        result = create_revenue_chart_widget(
            periods=["Jan", "Feb", "Mar"],
            values=[100.0, 150.0, 180.0],
        )
        current = result["data"]["currentPeriod"]
        assert current["revenue"] == 180.0
        assert current["change"] == 30.0
        assert current["changePercent"] == 20.0

    def test_handles_single_value(self):
        result = create_revenue_chart_widget(periods=["Jan"], values=[100.0])
        current = result["data"]["currentPeriod"]
        assert current["revenue"] == 100.0
        assert current["change"] == 0.0

    def test_returns_error_data_for_empty_values(self):
        result = create_revenue_chart_widget(periods=[], values=[])
        assert result["type"] == "revenue_chart"
        assert "error" in result["data"]

    def test_default_currency_is_usd(self):
        result = create_revenue_chart_widget(periods=["Jan"], values=[100.0])
        assert result["data"]["currency"] == "USD"

    def test_custom_currency(self):
        result = create_revenue_chart_widget(periods=["Jan"], values=[100.0], currency="EUR")
        assert result["data"]["currency"] == "EUR"


# =============================================================================
# create_product_launch_widget
# =============================================================================

class TestCreateProductLaunchWidget:
    def test_returns_product_launch_type(self):
        milestones = json.dumps([
            {"name": "Beta", "date": "2026-03-01", "status": "completed"},
        ])
        result = create_product_launch_widget(milestones=milestones)
        assert result["type"] == "product_launch"
        assert result["title"] == "Product Launch Tracker"

    def test_detects_delayed_status(self):
        milestones = json.dumps([
            {"name": "Beta", "date": "2026-03-01", "status": "delayed"},
            {"name": "GA", "date": "2026-04-01", "status": "pending"},
        ])
        result = create_product_launch_widget(milestones=milestones)
        assert result["data"]["status"] == "delayed"

    def test_detects_on_track_status(self):
        milestones = json.dumps([
            {"name": "Beta", "date": "2026-03-01", "status": "completed"},
            {"name": "GA", "date": "2026-04-01", "status": "pending"},
        ])
        result = create_product_launch_widget(milestones=milestones)
        assert result["data"]["status"] == "on_track"


# =============================================================================
# create_kanban_board_widget
# =============================================================================

class TestCreateKanbanBoardWidget:
    def test_returns_kanban_board_type(self):
        cols = json.dumps([{"id": "todo", "title": "To Do"}])
        cards = json.dumps([{"id": "1", "columnId": "todo", "title": "Task 1"}])
        result = create_kanban_board_widget(columns=cols, cards=cards)
        assert result["type"] == "kanban_board"
        assert result["title"] == "Project Board"
        assert len(result["data"]["columns"]) == 1
        assert len(result["data"]["cards"]) == 1


# =============================================================================
# create_workflow_builder_widget
# =============================================================================

class TestCreateWorkflowBuilderWidget:
    def test_returns_workflow_builder_type(self):
        result = create_workflow_builder_widget()
        assert result["type"] == "workflow_builder"
        assert result["title"] == "Workflow Builder"

    def test_processes_nodes_with_data_label(self):
        nodes = json.dumps([
            {"id": "n1", "data": {"label": "Start"}, "position": {"x": 0, "y": 0}},
        ])
        result = create_workflow_builder_widget(nodes=nodes)
        assert len(result["data"]["nodes"]) == 1
        assert result["data"]["nodes"][0]["data"]["label"] == "Start"

    def test_processes_nodes_with_legacy_top_level_label(self):
        nodes = json.dumps([{"id": "n1", "label": "Legacy Step"}])
        result = create_workflow_builder_widget(nodes=nodes)
        assert result["data"]["nodes"][0]["data"]["label"] == "Legacy Step"

    def test_generates_default_label_when_missing(self):
        nodes = json.dumps([{"id": "n1"}])
        result = create_workflow_builder_widget(nodes=nodes)
        assert result["data"]["nodes"][0]["data"]["label"] == "Step 1"

    def test_processes_edges(self):
        edges = json.dumps([{"source": "n1", "target": "n2"}])
        result = create_workflow_builder_widget(edges=edges)
        assert len(result["data"]["edges"]) == 1
        assert result["data"]["edges"][0]["source"] == "n1"

    def test_skips_edges_without_source_or_target(self):
        edges = json.dumps([{"source": "n1"}, {"target": "n2"}])
        result = create_workflow_builder_widget(edges=edges)
        assert len(result["data"]["edges"]) == 0

    def test_skips_non_dict_entries(self):
        nodes = json.dumps(["not a dict", {"id": "n1", "label": "Real"}])
        edges = json.dumps(["bad", {"source": "a", "target": "b"}])
        result = create_workflow_builder_widget(nodes=nodes, edges=edges)
        assert len(result["data"]["nodes"]) == 1
        assert len(result["data"]["edges"]) == 1


# =============================================================================
# create_morning_briefing_widget
# =============================================================================

class TestCreateMorningBriefingWidget:
    def test_returns_morning_briefing_type(self):
        result = create_morning_briefing_widget(
            greeting="Good morning!",
            pending_approvals="[]",
            online_agents=5,
            system_status="healthy",
        )
        assert result["type"] == "morning_briefing"
        assert result["data"]["greeting"] == "Good morning!"
        assert result["data"]["online_agents"] == 5
        assert result["data"]["system_status"] == "healthy"

    def test_normalizes_pending_approvals(self):
        approvals = json.dumps([
            {"id": "a1", "action_type": "deploy", "created_at": "2026-03-20", "token": "tok-1"},
        ])
        result = create_morning_briefing_widget(
            greeting="Hi",
            pending_approvals=approvals,
            online_agents=3,
            system_status="ok",
        )
        normalized = result["data"]["pending_approvals"]
        assert len(normalized) == 1
        assert normalized[0]["action_type"] == "deploy"

    def test_not_expandable(self):
        result = create_morning_briefing_widget(
            greeting="Hi", pending_approvals="[]",
            online_agents=1, system_status="ok",
        )
        assert result["expandable"] is False


# =============================================================================
# create_boardroom_widget
# =============================================================================

class TestCreateBoardroomWidget:
    def test_returns_boardroom_type(self):
        transcript = json.dumps([
            {"speaker": "CFO", "content": "Revenue is up"},
        ])
        result = create_boardroom_widget(
            topic="Q1 Review",
            transcript=transcript,
            verdict="Proceed with expansion",
        )
        assert result["type"] == "boardroom"
        assert result["data"]["topic"] == "Q1 Review"
        assert result["data"]["verdict"] == "Proceed with expansion"
        assert len(result["data"]["transcript"]) == 1

    def test_normalizes_legacy_text_field(self):
        transcript = json.dumps([{"speaker": "CEO", "text": "Legacy text"}])
        result = create_boardroom_widget(topic="T", transcript=transcript, verdict="V")
        assert result["data"]["transcript"][0]["content"] == "Legacy text"


# =============================================================================
# create_suggested_workflows_widget
# =============================================================================

class TestCreateSuggestedWorkflowsWidget:
    def test_returns_suggested_workflows_type(self):
        suggestions = json.dumps([
            {"id": "s1", "pattern_description": "Weekly report", "suggested_goal": "Automate", "status": "suggested"},
        ])
        result = create_suggested_workflows_widget(suggestions=suggestions)
        assert result["type"] == "suggested_workflows"
        assert len(result["data"]["suggestions"]) == 1

    def test_generates_ids_when_missing(self):
        suggestions = json.dumps([{"name": "Test suggestion"}])
        result = create_suggested_workflows_widget(suggestions=suggestions)
        assert result["data"]["suggestions"][0]["id"].startswith("suggestion-")


# =============================================================================
# create_form_widget
# =============================================================================

class TestCreateFormWidget:
    def test_returns_form_type(self):
        fields = json.dumps([{"name": "email", "label": "Email", "type": "email"}])
        result = create_form_widget(fields=fields)
        assert result["type"] == "form"
        assert result["data"]["submitLabel"] == "Submit"

    def test_custom_submit_label(self):
        fields = json.dumps([])
        result = create_form_widget(fields=fields, submit_label="Send")
        assert result["data"]["submitLabel"] == "Send"

    def test_not_expandable(self):
        result = create_form_widget(fields="[]")
        assert result["expandable"] is False


# =============================================================================
# create_table_widget
# =============================================================================

class TestCreateTableWidget:
    def test_returns_table_type(self):
        columns = json.dumps([{"key": "name", "label": "Name"}])
        rows = json.dumps([{"name": "Alice"}])
        result = create_table_widget(columns=columns, rows=rows)
        assert result["type"] == "table"
        assert result["title"] == "Data Table"
        assert len(result["data"]["columns"]) == 1
        assert len(result["data"]["rows"]) == 1

    def test_custom_title(self):
        result = create_table_widget(columns="[]", rows="[]", title="Custom Table")
        assert result["title"] == "Custom Table"

    def test_actions_default_to_empty(self):
        result = create_table_widget(columns="[]", rows="[]")
        assert result["data"]["actions"] == []


# =============================================================================
# create_calendar_widget
# =============================================================================

class TestCreateCalendarWidget:
    def test_returns_calendar_type(self):
        events = json.dumps([
            {"title": "Meeting", "start": "2026-03-20T10:00:00", "end": "2026-03-20T11:00:00"},
        ])
        result = create_calendar_widget(events=events)
        assert result["type"] == "calendar"
        assert result["data"]["view"] == "month"
        assert len(result["data"]["events"]) == 1

    def test_custom_view(self):
        result = create_calendar_widget(events="[]", view="week")
        assert result["data"]["view"] == "week"


# =============================================================================
# display_workflow_observability
# =============================================================================

class TestDisplayWorkflowObservability:
    def test_returns_observability_widget(self):
        result = display_workflow_observability()
        assert result["type"] == "workflow_observability"
        assert result["title"] == "Pipeline Health"
        assert result["data"] == {}
        assert result["dismissible"] is True


# =============================================================================
# display_workflow_timeline
# =============================================================================

class TestDisplayWorkflowTimeline:
    def test_returns_timeline_widget(self):
        result = display_workflow_timeline(execution_id="exec-456")
        assert result["type"] == "workflow_timeline"
        assert result["data"]["execution_id"] == "exec-456"
        assert result["title"] == "Execution Timeline"


# =============================================================================
# create_campaign_hub_widget
# =============================================================================

class TestCreateCampaignHubWidget:
    def test_returns_campaign_hub_type(self):
        result = create_campaign_hub_widget(campaign_name="Spring Sale")
        assert result["type"] == "campaign_hub"
        assert result["title"] == "Campaign Hub"

    def test_includes_campaign_data_when_name_provided(self):
        result = create_campaign_hub_widget(
            campaign_name="Launch",
            campaign_status="active",
            target_audience="Developers",
        )
        campaign = result["data"]["campaign"]
        assert campaign["name"] == "Launch"
        assert campaign["status"] == "active"
        assert campaign["target_audience"] == "Developers"

    def test_omits_campaign_when_no_name(self):
        result = create_campaign_hub_widget()
        assert "campaign" not in result["data"]

    def test_includes_metrics_when_provided(self):
        result = create_campaign_hub_widget(
            campaign_name="Test",
            impressions=1000,
            clicks=50,
            conversions=5,
            ctr=5.0,
        )
        metrics = result["data"]["campaign"]["metrics"]
        assert metrics["impressions"] == 1000
        assert metrics["clicks"] == 50
        assert metrics["ctr"] == 5.0

    def test_includes_stats_when_provided(self):
        stats_json = json.dumps([{"label": "Followers", "value": "10K", "trend": "up"}])
        result = create_campaign_hub_widget(stats=stats_json)
        assert len(result["data"]["stats"]) == 1

    def test_includes_content_pipeline(self):
        items = json.dumps([{"type": "blog", "title": "Post 1", "status": "draft"}])
        result = create_campaign_hub_widget(pipeline_items=items, pipeline_phase="Draft")
        pipeline = result["data"]["content_pipeline"]
        assert pipeline["phase"] == "Draft"
        assert len(pipeline["items"]) == 1

    def test_assigns_ids_to_news_items_without_id(self):
        news = json.dumps([{"headline": "Breaking", "source": "CNN", "published_at": "now", "summary": "..."}])
        result = create_campaign_hub_widget(news_feed=news)
        assert result["data"]["news_feed"][0]["id"] == "news-1"
