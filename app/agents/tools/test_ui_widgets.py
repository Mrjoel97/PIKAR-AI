# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""
Unit tests for UI Widget Tools.

Tests all widget creation tools to ensure they return valid widget definitions
that match the frontend's WidgetRegistry expectations.
"""

from app.agents.tools.ui_widgets import (
    UI_WIDGET_TOOLS,
    create_boardroom_widget,
    create_calendar_widget,
    create_form_widget,
    create_initiative_dashboard_widget,
    create_kanban_board_widget,
    create_morning_briefing_widget,
    create_product_launch_widget,
    create_revenue_chart_widget,
    create_suggested_workflows_widget,
    create_table_widget,
    create_workflow_builder_widget,
    display_workflow,
)

# Valid widget types (must match frontend WidgetRegistry)
VALID_WIDGET_TYPES = {
    "initiative_dashboard",
    "revenue_chart",
    "product_launch",
    "kanban_board",
    "workflow_builder",
    "morning_briefing",
    "boardroom",
    "suggested_workflows",
    "form",
    "table",
    "calendar",
    "workflow",
}


def _assert_valid_widget(result: dict, expected_type: str):
    """Helper: assert a tool result is a valid widget definition."""
    assert isinstance(result, dict), "Tool result must be a dict"
    assert result.get("type") == expected_type, (
        f"Expected type '{expected_type}', got '{result.get('type')}'"
    )
    assert isinstance(result.get("data"), dict), "Widget must have a 'data' dict"
    assert result["type"] in VALID_WIDGET_TYPES, (
        f"Widget type '{result['type']}' not in valid types"
    )


class TestInitiativeDashboardWidget:
    """Tests for create_initiative_dashboard_widget tool."""

    def test_returns_valid_widget(self):
        result = create_initiative_dashboard_widget(
            initiatives=[
                {
                    "id": "1",
                    "name": "Project A",
                    "status": "in_progress",
                    "progress": 75,
                },
            ]
        )
        _assert_valid_widget(result, "initiative_dashboard")

    def test_has_metrics(self):
        result = create_initiative_dashboard_widget(
            initiatives=[
                {"id": "1", "name": "A", "status": "completed", "progress": 100},
                {"id": "2", "name": "B", "status": "blocked", "progress": 30},
            ]
        )
        metrics = result["data"]["metrics"]
        assert metrics["total"] == 2
        assert metrics["completed"] == 1
        assert metrics["blocked"] == 1

    def test_empty_initiatives(self):
        result = create_initiative_dashboard_widget(initiatives=[])
        assert result["data"]["initiatives"] == []
        assert result["data"]["metrics"]["total"] == 0

    def test_preserves_operational_state_fields(self):
        result = create_initiative_dashboard_widget(
            initiatives=[
                {
                    "id": "1",
                    "title": "Launch Ops",
                    "status": "in_progress",
                    "progress": 55,
                    "goal": "Ship the new launch workflow",
                    "current_phase": "validation",
                    "success_criteria": ["Page live", "Tracking verified"],
                    "primary_workflow": "Landing Page to Launch",
                    "deliverables": ["landing-page"],
                    "evidence": [{"type": "url", "value": "https://example.com"}],
                    "blockers": [{"message": "Awaiting approval"}],
                    "next_actions": ["Get final sign-off"],
                    "trust_summary": {"approval_state": "pending"},
                    "verification_status": "pending",
                },
            ]
        )
        initiative = result["data"]["initiatives"][0]
        assert initiative["goal"] == "Ship the new launch workflow"
        assert initiative["currentPhase"] == "validation"
        assert initiative["primaryWorkflow"] == "Landing Page to Launch"
        assert initiative["trustSummary"]["approval_state"] == "pending"
        assert initiative["verificationStatus"] == "pending"


class TestRevenueChartWidget:
    """Tests for create_revenue_chart_widget tool."""

    def test_returns_valid_widget(self):
        result = create_revenue_chart_widget(
            periods=["Jan", "Feb", "Mar"], values=[1000, 1500, 2000]
        )
        _assert_valid_widget(result, "revenue_chart")

    def test_has_current_period(self):
        result = create_revenue_chart_widget(
            periods=["Jan", "Feb"], values=[1000, 1500]
        )
        cp = result["data"]["currentPeriod"]
        assert cp["revenue"] == 1500
        assert cp["change"] == 500
        assert cp["changePercent"] == 50.0

    def test_currency_default(self):
        result = create_revenue_chart_widget(periods=["Jan"], values=[100])
        assert result["data"]["currency"] == "USD"

    def test_custom_currency(self):
        result = create_revenue_chart_widget(
            periods=["Jan"], values=[100], currency="EUR"
        )
        assert result["data"]["currency"] == "EUR"

    def test_empty_values(self):
        result = create_revenue_chart_widget(periods=[], values=[])
        # Should handle gracefully
        assert result["type"] == "revenue_chart"


class TestProductLaunchWidget:
    """Tests for create_product_launch_widget tool."""

    def test_returns_valid_widget(self):
        result = create_product_launch_widget(
            milestones=[
                {"name": "Design", "date": "2024-01-01", "status": "completed"},
                {"name": "Development", "date": "2024-03-01", "status": "in_progress"},
            ]
        )
        _assert_valid_widget(result, "product_launch")

    def test_status_on_track(self):
        result = create_product_launch_widget(
            milestones=[
                {"name": "M1", "date": "2024-01-01", "status": "completed"},
            ]
        )
        assert result["data"]["status"] == "on_track"

    def test_status_delayed(self):
        result = create_product_launch_widget(
            milestones=[
                {"name": "M1", "date": "2024-01-01", "status": "delayed"},
            ]
        )
        assert result["data"]["status"] == "delayed"


class TestKanbanBoardWidget:
    """Tests for create_kanban_board_widget tool."""

    def test_returns_valid_widget(self):
        result = create_kanban_board_widget(
            columns=[{"id": "todo", "title": "To Do"}],
            cards=[{"id": "c1", "columnId": "todo", "title": "Task 1"}],
        )
        _assert_valid_widget(result, "kanban_board")

    def test_data_structure(self):
        columns = [{"id": "todo", "title": "To Do"}]
        cards = [{"id": "c1", "columnId": "todo", "title": "Task 1"}]
        result = create_kanban_board_widget(columns=columns, cards=cards)
        assert result["data"]["columns"] == columns
        assert result["data"]["cards"] == cards


class TestWorkflowBuilderWidget:
    """Tests for create_workflow_builder_widget tool."""

    def test_returns_valid_widget(self):
        result = create_workflow_builder_widget()
        _assert_valid_widget(result, "workflow_builder")

    def test_defaults_to_empty_lists(self):
        result = create_workflow_builder_widget()
        assert result["data"]["nodes"] == []
        assert result["data"]["edges"] == []

    def test_passes_nodes_and_edges(self):
        nodes = [{"id": "1", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}}]
        edges = [{"id": "e1", "source": "1", "target": "2"}]
        result = create_workflow_builder_widget(nodes=nodes, edges=edges)
        assert result["data"]["nodes"] == nodes
        assert result["data"]["edges"] == edges

    def test_expandable(self):
        result = create_workflow_builder_widget()
        assert result["expandable"] is True


class TestMorningBriefingWidget:
    """Tests for create_morning_briefing_widget tool."""

    def test_returns_valid_widget(self):
        result = create_morning_briefing_widget(
            greeting="Good morning!",
            pending_approvals=[],
            online_agents=5,
            system_status="healthy",
        )
        _assert_valid_widget(result, "morning_briefing")

    def test_data_fields(self):
        result = create_morning_briefing_widget(
            greeting="Hello",
            pending_approvals=[
                {
                    "id": "1",
                    "action_type": "deploy",
                    "created_at": "2024-01-01",
                    "token": "abc",
                }
            ],
            online_agents=3,
            system_status="healthy",
        )
        assert result["data"]["greeting"] == "Hello"
        assert len(result["data"]["pending_approvals"]) == 1
        assert result["data"]["online_agents"] == 3


class TestBoardroomWidget:
    """Tests for create_boardroom_widget tool."""

    def test_returns_valid_widget(self):
        result = create_boardroom_widget(
            topic="Q3 Strategy",
            transcript=[
                {
                    "speaker": "CEO",
                    "content": "We need to focus...",
                    "sentiment": "positive",
                }
            ],
            verdict="Approved",
        )
        _assert_valid_widget(result, "boardroom")


class TestSuggestedWorkflowsWidget:
    """Tests for create_suggested_workflows_widget tool."""

    def test_returns_valid_widget(self):
        result = create_suggested_workflows_widget(
            suggestions=[
                {
                    "id": "s1",
                    "pattern_description": "Weekly review",
                    "suggested_goal": "...",
                    "suggested_context": "...",
                    "status": "new",
                }
            ]
        )
        _assert_valid_widget(result, "suggested_workflows")


class TestFormWidget:
    """Tests for create_form_widget tool."""

    def test_returns_valid_widget(self):
        result = create_form_widget(
            fields=[
                {"name": "email", "label": "Email", "type": "email", "required": True}
            ]
        )
        _assert_valid_widget(result, "form")

    def test_default_submit_label(self):
        result = create_form_widget(fields=[])
        assert result["data"]["submitLabel"] == "Submit"

    def test_custom_submit_label(self):
        result = create_form_widget(fields=[], submit_label="Send")
        assert result["data"]["submitLabel"] == "Send"


class TestTableWidget:
    """Tests for create_table_widget tool."""

    def test_returns_valid_widget(self):
        result = create_table_widget(
            columns=[{"key": "name", "label": "Name"}], rows=[{"name": "Alice"}]
        )
        _assert_valid_widget(result, "table")

    def test_custom_title(self):
        result = create_table_widget(columns=[], rows=[], title="Lead List")
        assert result["title"] == "Lead List"


class TestCalendarWidget:
    """Tests for create_calendar_widget tool."""

    def test_returns_valid_widget(self):
        result = create_calendar_widget(
            events=[
                {
                    "id": "e1",
                    "title": "Meeting",
                    "start": "2024-01-01",
                    "end": "2024-01-01",
                }
            ]
        )
        _assert_valid_widget(result, "calendar")

    def test_default_view(self):
        result = create_calendar_widget(events=[])
        assert result["data"]["view"] == "month"

    def test_custom_view(self):
        result = create_calendar_widget(events=[], view="week")
        assert result["data"]["view"] == "week"


class TestDisplayWorkflow:
    """Tests for display_workflow tool."""

    def test_returns_valid_widget(self):
        result = display_workflow(execution_id="exec-123")
        _assert_valid_widget(result, "workflow")

    def test_has_execution_id(self):
        result = display_workflow(execution_id="exec-123")
        assert result["data"]["execution_id"] == "exec-123"


class TestUIWidgetToolsExport:
    """Tests for the UI_WIDGET_TOOLS export."""

    def test_contains_all_tools(self):
        """Should export all 12 widget tools."""
        assert len(UI_WIDGET_TOOLS) == 12

    def test_tools_are_callable(self):
        """All tools should be callable functions."""
        for tool in UI_WIDGET_TOOLS:
            assert callable(tool)

    def test_tools_have_docstrings(self):
        """All tools should have docstrings for ADK introspection."""
        for tool in UI_WIDGET_TOOLS:
            assert tool.__doc__ is not None
            assert len(tool.__doc__) > 10

    def test_all_widget_types_covered(self):
        """At least one tool should produce each registered widget type."""
        produced_types = set()
        # Call each tool with minimal valid args and collect the types
        produced_types.add(create_initiative_dashboard_widget(initiatives=[])["type"])
        produced_types.add(create_revenue_chart_widget(periods=[], values=[])["type"])
        produced_types.add(create_product_launch_widget(milestones=[])["type"])
        produced_types.add(create_kanban_board_widget(columns=[], cards=[])["type"])
        produced_types.add(create_workflow_builder_widget()["type"])
        produced_types.add(
            create_morning_briefing_widget(
                greeting="", pending_approvals=[], online_agents=0, system_status="ok"
            )["type"]
        )
        produced_types.add(
            create_boardroom_widget(topic="", transcript=[], verdict="")["type"]
        )
        produced_types.add(create_suggested_workflows_widget(suggestions=[])["type"])
        produced_types.add(create_form_widget(fields=[])["type"])
        produced_types.add(create_table_widget(columns=[], rows=[])["type"])
        produced_types.add(create_calendar_widget(events=[])["type"])
        produced_types.add(display_workflow(execution_id="test")["type"])

        assert produced_types == VALID_WIDGET_TYPES
