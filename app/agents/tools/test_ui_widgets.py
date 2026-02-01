"""
Unit tests for UI Widget Tools.

Tests the display_dashboard, display_workflow_builder, and display_chart tools.
"""

import pytest
from app.agents.tools.ui_widgets import (
    display_dashboard,
    display_workflow_builder,
    display_chart,
    display_form,
    display_table,
    display_kanban,
    display_calendar,
    UI_WIDGET_TOOLS,
)


class TestDisplayDashboard:
    """Tests for display_dashboard tool."""

    def test_returns_widget_structure(self):
        """Should return a dict with widget and text keys."""
        result = display_dashboard(
            dashboard_type="initiative_dashboard",
            title="Q1 Initiatives",
            data={"initiatives": [], "metrics": {"total": 0}}
        )

        assert "widget" in result
        assert "text" in result

    def test_widget_has_required_fields(self):
        """Widget should have type, title, data, dismissible fields."""
        result = display_dashboard(
            dashboard_type="revenue_chart",
            title="Revenue Overview",
            data={"periods": ["Jan"], "values": [1000]}
        )

        widget = result["widget"]
        assert widget["type"] == "revenue_chart"
        assert widget["title"] == "Revenue Overview"
        assert widget["data"] == {"periods": ["Jan"], "values": [1000]}
        assert widget["dismissible"] is True

    def test_initiative_dashboard_type(self):
        """Should correctly set initiative_dashboard type."""
        result = display_dashboard(
            dashboard_type="initiative_dashboard",
            title="Test",
            data={}
        )

        assert result["widget"]["type"] == "initiative_dashboard"

    def test_revenue_chart_type(self):
        """Should correctly set revenue_chart type."""
        result = display_dashboard(
            dashboard_type="revenue_chart",
            title="Test",
            data={}
        )

        assert result["widget"]["type"] == "revenue_chart"

    def test_product_launch_type(self):
        """Should correctly set product_launch type."""
        result = display_dashboard(
            dashboard_type="product_launch",
            title="Test",
            data={}
        )

        assert result["widget"]["type"] == "product_launch"

    def test_text_includes_title(self):
        """Text message should include the title."""
        result = display_dashboard(
            dashboard_type="initiative_dashboard",
            title="My Dashboard",
            data={}
        )

        assert "My Dashboard" in result["text"]

    def test_passes_complex_data(self):
        """Should pass through complex data structures."""
        complex_data = {
            "initiatives": [
                {"id": "1", "name": "Project A", "status": "in_progress", "progress": 75},
                {"id": "2", "name": "Project B", "status": "completed", "progress": 100}
            ],
            "metrics": {
                "total": 2,
                "completed": 1,
                "in_progress": 1,
                "blocked": 0
            }
        }

        result = display_dashboard(
            dashboard_type="initiative_dashboard",
            title="Complex Test",
            data=complex_data
        )

        assert result["widget"]["data"] == complex_data


class TestDisplayWorkflowBuilder:
    """Tests for display_workflow_builder tool."""

    def test_returns_widget_structure(self):
        """Should return a dict with widget and text keys."""
        result = display_workflow_builder(title="Test Workflow")

        assert "widget" in result
        assert "text" in result

    def test_widget_type_is_workflow_builder(self):
        """Widget type should be workflow_builder."""
        result = display_workflow_builder(title="Test")

        assert result["widget"]["type"] == "workflow_builder"

    def test_default_empty_nodes_and_edges(self):
        """Should default to empty nodes and edges lists."""
        result = display_workflow_builder(title="Empty Workflow")

        assert result["widget"]["data"]["nodes"] == []
        assert result["widget"]["data"]["edges"] == []

    def test_passes_initial_nodes(self):
        """Should pass through initial nodes."""
        nodes = [
            {"id": "1", "position": {"x": 100, "y": 100}, "data": {"label": "Start"}}
        ]

        result = display_workflow_builder(title="Test", initial_nodes=nodes)

        assert result["widget"]["data"]["nodes"] == nodes

    def test_passes_initial_edges(self):
        """Should pass through initial edges."""
        edges = [
            {"id": "e1-2", "source": "1", "target": "2"}
        ]

        result = display_workflow_builder(
            title="Test",
            initial_nodes=[],
            initial_edges=edges
        )

        assert result["widget"]["data"]["edges"] == edges

    def test_expandable_is_true(self):
        """Workflow builder should be expandable."""
        result = display_workflow_builder(title="Test")

        assert result["widget"]["expandable"] is True

    def test_text_includes_title(self):
        """Text message should include workflow title."""
        result = display_workflow_builder(title="Lead Generation Flow")

        assert "Lead Generation Flow" in result["text"]


class TestDisplayChart:
    """Tests for display_chart tool."""

    def test_returns_widget_structure(self):
        """Should return a dict with widget and text keys."""
        result = display_chart(
            chart_type="bar",
            title="Sales Chart",
            labels=["Q1", "Q2"],
            values=[100, 150]
        )

        assert "widget" in result
        assert "text" in result

    def test_widget_uses_revenue_chart_type(self):
        """Widget type should be revenue_chart (since it supports charts)."""
        result = display_chart(
            chart_type="bar",
            title="Test",
            labels=[],
            values=[]
        )

        assert result["widget"]["type"] == "revenue_chart"

    def test_passes_chart_type_in_data(self):
        """Should pass chart_type in data."""
        result = display_chart(
            chart_type="line",
            title="Test",
            labels=["A", "B"],
            values=[1, 2]
        )

        assert result["widget"]["data"]["chartType"] == "line"

    def test_passes_labels_as_periods(self):
        """Labels should be passed as periods."""
        result = display_chart(
            chart_type="bar",
            title="Test",
            labels=["Jan", "Feb", "Mar"],
            values=[10, 20, 30]
        )

        assert result["widget"]["data"]["periods"] == ["Jan", "Feb", "Mar"]

    def test_passes_values(self):
        """Values should be passed in data."""
        result = display_chart(
            chart_type="bar",
            title="Test",
            labels=["A"],
            values=[42.5]
        )

        assert result["widget"]["data"]["values"] == [42.5]

    def test_merges_options(self):
        """Should merge additional options into data."""
        result = display_chart(
            chart_type="pie",
            title="Test",
            labels=["A", "B"],
            values=[30, 70],
            options={"currency": "EUR", "showLegend": True}
        )

        assert result["widget"]["data"]["currency"] == "EUR"
        assert result["widget"]["data"]["showLegend"] is True

    def test_text_includes_title(self):
        """Text message should include chart title."""
        result = display_chart(
            chart_type="bar",
            title="Quarterly Revenue",
            labels=[],
            values=[]
        )

        assert "Quarterly Revenue" in result["text"]


class TestDisplayForm:
    """Tests for display_form tool."""

    def test_returns_widget_structure(self):
        """Should return a dict with widget and text keys."""
        result = display_form(
            title="Feedback Form",
            fields=[{"name": "feedback", "label": "Feedback", "type": "text"}]
        )

        assert "widget" in result
        assert "text" in result

    def test_widget_type_is_form(self):
        """Widget type should be form."""
        result = display_form(title="Test", fields=[])
        assert result["widget"]["type"] == "form"

    def test_passes_fields(self):
        """Should pass fields structure."""
        fields = [
            {"name": "name", "label": "Name", "type": "text", "required": True},
            {"name": "age", "label": "Age", "type": "number"}
        ]
        result = display_form(title="Test", fields=fields)
        
        assert result["widget"]["data"]["fields"] == fields

    def test_default_submit_label(self):
        """Should have default submit label."""
        result = display_form(title="Test", fields=[])
        assert result["widget"]["data"]["submitLabel"] == "Submit"

    def test_custom_submit_label(self):
        """Should allow custom submit label."""
        result = display_form(title="Test", fields=[], submit_label="Send")
        assert result["widget"]["data"]["submitLabel"] == "Send"


class TestDisplayTable:
    """Tests for display_table tool."""

    def test_returns_widget_structure(self):
        """Should return a dict with widget and text keys."""
        result = display_table(
            title="Lead List",
            columns=[{"key": "name", "label": "Name"}],
            rows=[{"name": "Alice"}]
        )

        assert "widget" in result
        assert "text" in result

    def test_widget_type_is_table(self):
        """Widget type should be table."""
        result = display_table(title="Test", columns=[], rows=[])
        assert result["widget"]["type"] == "table"

    def test_passes_data(self):
        """Should pass columns, rows, and actions."""
        columns = [{"key": "id", "label": "ID"}]
        rows = [{"id": 1}, {"id": 2}]
        actions = [{"name": "view", "label": "View"}]
        
        result = display_table(title="Test", columns=columns, rows=rows, actions=actions)
        
        assert result["widget"]["data"]["columns"] == columns
        assert result["widget"]["data"]["rows"] == rows
        assert result["widget"]["data"]["actions"] == actions

    def test_default_actions_empty(self):
        """Should default actions to empty list."""
        result = display_table(title="Test", columns=[], rows=[])
        assert result["widget"]["data"]["actions"] == []


class TestDisplayKanban:
    """Tests for display_kanban tool."""

    def test_returns_widget_structure(self):
        """Should return a dict with widget and text keys."""
        result = display_kanban(
            title="Project Board",
            columns=[{"id": "todo", "title": "To Do"}],
            cards=[]
        )

        assert "widget" in result
        assert "text" in result

    def test_widget_type_is_kanban(self):
        """Widget type should be kanban."""
        result = display_kanban(title="Test", columns=[], cards=[])
        assert result["widget"]["type"] == "kanban"

    def test_passes_data(self):
        """Should pass columns and cards."""
        columns = [{"id": "todo", "title": "To Do"}]
        cards = [{"id": "c1", "title": "Task 1", "columnId": "todo"}]
        
        result = display_kanban(title="Test", columns=columns, cards=cards)
        
        assert result["widget"]["data"]["columns"] == columns
        assert result["widget"]["data"]["cards"] == cards


class TestDisplayCalendar:
    """Tests for display_calendar tool."""

    def test_returns_widget_structure(self):
        """Should return a dict with widget and text keys."""
        result = display_calendar(
            title="Schedule",
            events=[{"id": "e1", "title": "Meeting", "start": "2023-01-01", "end": "2023-01-01"}]
        )

        assert "widget" in result
        assert "text" in result

    def test_widget_type_is_calendar(self):
        """Widget type should be calendar."""
        result = display_calendar(title="Test", events=[])
        assert result["widget"]["type"] == "calendar"

    def test_passes_events(self):
        """Should pass events and view."""
        events = [{"id": "e1", "title": "Meeting"}]
        view = "week"
        
        result = display_calendar(title="Test", events=events, view=view)
        
        assert result["widget"]["data"]["events"] == events
        assert result["widget"]["data"]["view"] == view


class TestUIWidgetToolsExport:
    """Tests for the UI_WIDGET_TOOLS export."""

    def test_contains_all_tools(self):
        """Should export all seven widget tools."""
        assert len(UI_WIDGET_TOOLS) == 7

    def test_contains_new_widgets(self):
        """Should contain all new widgets."""
        assert display_form in UI_WIDGET_TOOLS
        assert display_table in UI_WIDGET_TOOLS
        assert display_kanban in UI_WIDGET_TOOLS
        assert display_calendar in UI_WIDGET_TOOLS

    def test_tools_are_callable(self):
        """All tools should be callable functions."""
        for tool in UI_WIDGET_TOOLS:
            assert callable(tool)

    def test_tools_have_docstrings(self):
        """All tools should have docstrings for ADK."""
        for tool in UI_WIDGET_TOOLS:
            assert tool.__doc__ is not None
            assert len(tool.__doc__) > 50  # Reasonable docstring length
