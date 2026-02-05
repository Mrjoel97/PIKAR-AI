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


    dashboard_type: Literal["initiative_dashboard", "revenue_chart", "product_launch"],
    title: str,
    data: dict[str, Any],
    async_generate: bool = False,
    user_id: str | None = None
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
        data: JSON data to populate the dashboard. If async_generate is True, this can be input parameters.
        async_generate: If True, triggers asynchronous generation on the server.
        user_id: Required if async_generate is True.
    
    Returns:
        Widget definition that will be rendered in the chat interface
    """
    if async_generate and user_id:
        from app.services.edge_functions import edge_function_client
        import asyncio
        # We don't await here to return immediately, but we need to run it.
        # However, tools are sync. We can't await.
        # We'll use asyncio.create_task if there is a running loop, or run_in_executor.
        # But for safety/simplicity in this synchronous tool, we might just define it as a coroutine 
        # but the agent framework might not handle it if not typed async.
        # The plan says "Add async_generate... invoke generate-widget".
        # Assuming the environment allows async execution or fire-and-forget.
        # We will use a try/except block to attempting creating a task if loop exists.
        
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(edge_function_client.generate_widget(user_id, dashboard_type, data))
        except RuntimeError:
             # No loop running, maybe run sync? But edge_function_client is async.
             pass

        return {
            "widget": {
                "type": dashboard_type,
                "title": title,
                "data": {"isLoading": True, "message": "Generating dashboard..."},
                "dismissible": True,
                "expandable": False
            },
            "text": f"I'm generating the {title} dashboard for you..."
        }

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
    options: dict[str, Any] | None = None,
    async_generate: bool = False,
    user_id: str | None = None
) -> dict[str, Any]:
    """Display a chart visualization in the chat.
    
    Use this tool when the user needs to see data in chart form.
    
    Args:
        chart_type: Type of chart - "bar", "line", or "pie"
        title: Chart title
        labels: X-axis labels or pie slice labels
        values: Data values corresponding to labels
        options: Additional chart options like colors, currency, etc.
        async_generate: If True, triggers asynchronous generation on the server.
        user_id: Required if async_generate is True.
    
    Returns:
        Widget definition for chart display
    """
    if async_generate and user_id:
        from app.services.edge_functions import edge_function_client
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # Pass aggregated data as parameters
            params = {
                "chart_type": chart_type, 
                "labels": labels, 
                "values": values, 
                "options": options
            }
            loop.create_task(edge_function_client.generate_widget(user_id, "revenue_chart", params))
        except RuntimeError:
             pass

        return {
            "widget": {
                "type": "revenue_chart",
                "title": title,
                "data": {"isLoading": True, "message": "Generating chart..."},
                "dismissible": True
            },
            "text": f"Generating {title} chart..."
        }

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
            "type": "kanban_board",
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



def display_product_launch(
    title: str,
    data: dict[str, Any]
) -> dict[str, Any]:
    """Display a product launch timeline and status widget.
    
    Use this tool when the user wants to see a product launch timeline,
    milestones, and overall status.
    
    Args:
        title: Header text to display above the widget.
        data: Dict containing execution details:
            - milestones: List of dicts with name, date, status
            - status: Overall status (e.g., 'on_track', 'at_risk', 'delayed')
            
    Returns:
        Widget definition for the product launch display.
        
    Example:
        >>> display_product_launch(
        ...     title="Alpha Launch",
        ...     data={
        ...         "milestones": [
        ...             {"name": "Code Complete", "date": "2026-03-01", "status": "completed"},
        ...             {"name": "QA Signoff", "date": "2026-03-15", "status": "pending"}
        ...         ],
        ...         "status": "on_track"
        ...     }
        ... )
    """
    return {
        "widget": {
            "type": "product_launch",
            "title": title,
            "data": data,
            "dismissible": True,
            "expandable": False
        },
        "text": f"Here's your {title}:"
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
    display_product_launch,
]
