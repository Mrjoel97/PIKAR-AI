"""
UI Widget Tools for Agent-to-UI Feature.

These tools allow agents to generate interactive UI widgets that render
inline within the chat interface. Users can interact with these widgets
while continuing to chat with the agent.

Usage:
    from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
    
    agent = Agent(
        tools=[*UI_WIDGET_TOOLS, ...],
        ...
    )
"""

from typing import Literal, Any


def display_dashboard(
    dashboard_type: Literal["initiative_dashboard", "revenue_chart", "product_launch"],
    title: str,
    data: dict[str, Any]
) -> dict[str, Any]:
    """Display an interactive dashboard widget in the chat.
    
    Use this tool when the user asks to see business metrics, initiative status,
    revenue data, or any visual dashboard that would be better as an interactive
    UI component than as plain text.
    
    Args:
        dashboard_type: Type of dashboard to display. Must be one of:
            - "initiative_dashboard": Shows OKRs, projects, and their statuses
            - "revenue_chart": Shows revenue metrics with charts
            - "product_launch": Shows product launch timeline and status
        title: Header text to display above the widget
        data: JSON data to populate the dashboard. Structure depends on type:
            For initiative_dashboard: {
                "initiatives": [{"id": "...", "name": "...", "status": "in_progress|completed|blocked", "progress": 65}],
                "metrics": {"total": 5, "completed": 2, "in_progress": 2, "blocked": 1}
            }
            For revenue_chart: {
                "periods": ["Jan", "Feb", "Mar"],
                "values": [45000, 52000, 61000],
                "currency": "USD",
                "currentPeriod": {"revenue": 61000, "change": 9000, "changePercent": 17.3}
            }
            For product_launch: {
                "milestones": [{"name": "...", "date": "...", "status": "..."}],
                "status": "on_track|at_risk|delayed"
            }
    
    Returns:
        Widget definition that will be rendered in the chat interface
        
    Example:
        >>> display_dashboard(
        ...     dashboard_type="initiative_dashboard",
        ...     title="Q1 2026 Initiatives",
        ...     data={
        ...         "initiatives": [
        ...             {"id": "1", "name": "Product Launch", "status": "in_progress", "progress": 65},
        ...             {"id": "2", "name": "Hiring Sprint", "status": "completed", "progress": 100}
        ...         ],
        ...         "metrics": {"total": 2, "completed": 1, "in_progress": 1, "blocked": 0}
        ...     }
        ... )
    """
    return {
        "widget": {
            "type": dashboard_type,
            "title": title,
            "data": data,
            "dismissible": True,
            "expandable": False
        },
        "text": f"Here's your {title}:"
    }


def display_workflow_builder(
    title: str,
    initial_nodes: list[dict[str, Any]] | None = None,
    initial_edges: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Generate an interactive workflow builder in the chat.
    
    Use this tool when the user wants to create, edit, or visualize a workflow
    or process. The workflow builder allows users to see and interact with
    the workflow structure.
    
    Args:
        title: Name of the workflow being built
        initial_nodes: List of node definitions. Each node should have:
            - id: Unique identifier
            - position: {"x": number, "y": number}
            - data: {"label": "Node name"}
        initial_edges: List of edge connections. Each edge should have:
            - id: Unique identifier
            - source: Source node id
            - target: Target node id
    
    Returns:
        Widget definition for workflow builder
        
    Example:
        >>> display_workflow_builder(
        ...     title="Lead Generation Workflow",
        ...     initial_nodes=[
        ...         {"id": "1", "position": {"x": 100, "y": 100}, "data": {"label": "Receive Lead"}},
        ...         {"id": "2", "position": {"x": 100, "y": 200}, "data": {"label": "Qualify Lead"}},
        ...         {"id": "3", "position": {"x": 100, "y": 300}, "data": {"label": "Send Proposal"}}
        ...     ],
        ...     initial_edges=[
        ...         {"id": "e1-2", "source": "1", "target": "2"},
        ...         {"id": "e2-3", "source": "2", "target": "3"}
        ...     ]
        ... )
    """
    nodes = initial_nodes or []
    edges = initial_edges or []
    
    return {
        "widget": {
            "type": "workflow_builder",
            "title": title,
            "data": {
                "nodes": nodes,
                "edges": edges
            },
            "dismissible": True,
            "expandable": True
        },
        "text": f"I've created a workflow builder for '{title}'. You can view and edit it directly!"
    }


def display_chart(
    chart_type: Literal["bar", "line", "pie"],
    title: str,
    labels: list[str],
    values: list[float],
    options: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Display a chart visualization in the chat.
    
    Use this tool when the user needs to see data in chart form.
    
    Args:
        chart_type: Type of chart - "bar", "line", or "pie"
        title: Chart title
        labels: X-axis labels or pie slice labels
        values: Data values corresponding to labels
        options: Additional chart options like colors, currency, etc.
    
    Returns:
        Widget definition for chart display
    """
    return {
        "widget": {
            "type": "revenue_chart",  # Using revenue_chart as it supports charts
            "title": title,
            "data": {
                "periods": labels,
                "values": values,
                "chartType": chart_type,
                **(options or {})
            },
            "dismissible": True
        },
        "text": f"Here's the {title} chart:"
    }


# Export tools
def display_form(
    title: str,
    fields: list[dict[str, str | bool | list[str]]],
    submit_label: str = "Submit"
) -> dict[str, Any]:
    """Display an interactive form for data collection.
    
    Args:
        title: Title of the form.
        fields: List of field definitions. Each dict contains:
            - name: Field identifier
            - label: Display label
            - type: 'text', 'number', 'email', 'select', 'textarea', 'date'
            - required: Boolean (optional)
            - options: List of strings (for select type)
        submit_label: Label for the submit button.
        
    Returns:
        Dict with widget definition.
    """
    return {
        "widget": {
            "type": "form",
            "title": title,
            "data": {
                "fields": fields,
                "submitLabel": submit_label,
            },
            "dismissible": True,
            "expandable": False,
        },
        "text": f"I've opened the '{title}' form for you to fill out."
    }


def display_table(
    title: str,
    columns: list[dict[str, str | bool]],
    rows: list[dict[str, Any]],
    actions: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    """Display a data table with optional actions.
    
    Args:
        title: Title of the table.
        columns: List of column definitions:
            - key: Data key matching row data
            - label: Display header
            - sortable: Boolean
        rows: List of data objects.
        actions: Optional list of row actions:
            - name: Action identifier (e.g., 'view', 'delete')
            - label: Button tooltip
            
    Returns:
        Dict with widget definition.
    """
    return {
        "widget": {
            "type": "table",
            "title": title,
            "data": {
                "columns": columns,
                "rows": rows,
                "actions": actions or [],
            },
            "dismissible": True,
            "expandable": True,
        },
        "text": f"Here is the '{title}' table."
    }


def display_kanban(
    title: str,
    columns: list[dict[str, str]],
    cards: list[dict[str, str | list[str]]]
) -> dict[str, Any]:
    """Display a Kanban board for task management.
    
    Args:
        title: Title of the board.
        columns: List of columns, each dict having:
            - id: Column identifier
            - title: Display title
            - color: Optional Tailwind bg class
        cards: List of cards, each having:
            - id: Card identifier
            - columnId: Which column it belongs to
            - title: Card title
            - description: Optional details
            - tags: Optional list of tag strings
            
    Returns:
        Dict with widget definition.
    """
    return {
        "widget": {
            "type": "kanban",
            "title": title,
            "data": {
                "columns": columns,
                "cards": cards,
            },
            "dismissible": True,
            "expandable": True,
        },
        "text": f"I've updated the '{title}' board."
    }


def display_calendar(
    title: str,
    events: list[dict[str, str]],
    view: str = "month"
) -> dict[str, Any]:
    """Display a calendar for scheduling and events.
    
    Args:
        title: Title of the calendar (e.g., 'Content Schedule').
        events: List of event dicts, each containing:
            - id: Event ID
            - title: Event title
            - start: Start timestamp (ISO string)
            - end: End timestamp (ISO string)
            - color: Optional color class
        view: Default view 'month', 'week', or 'day'.
        
    Returns:
        Dict with widget definition.
    """
    return {
        "widget": {
            "type": "calendar",
            "title": title,
            "data": {
                "events": events,
                "view": view,
            },
            "dismissible": True,
            "expandable": True,
        },
        "text": f"I've opened the '{title}' calendar."
    }


# Export available widgets
UI_WIDGET_TOOLS = [
    display_dashboard,
    display_workflow_builder,
    display_chart,
    display_form,
    display_table,
    display_kanban,
    display_calendar,
]
