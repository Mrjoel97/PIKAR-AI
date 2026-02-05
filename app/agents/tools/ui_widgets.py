from typing import List, Dict, Any, Optional
import random
from app.agents.tools.base import agent_tool
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Widget Types
WIDGET_TYPES = [
    'initiative_dashboard',
    'revenue_chart',
    'product_launch',
    'kanban_board', 
    'workflow_builder',
    'morning_briefing',
    'boardroom',
    'suggested_workflows',
    'form',
    'table',
    'calendar',
    'workflow'
]

@agent_tool
def display_workflow(execution_id: str) -> Dict[str, Any]:
    """Displays a workflow progress widget for a given execution ID.
    
    Args:
        execution_id: The ID of the workflow execution to display.
    """
    try:
        from app.workflows.engine import get_workflow_engine
        import asyncio
        
        # We need async context to call engine methods if they are async.
        # tools are typically synchronous or handle async differently. 
        # If this tool is run in a sync context by the agent executor, we need to run_until_complete or similar if allowed.
        # Alternatively, likely the tool execution environment handles async tools or we use sync wrapper.
        # Assuming we can't easily call async engine here without async wiring.
        # But wait, `ui_widgets.py` usually returns static definitions.
        # If I need to fetch data, I might need to access DB directly or rely on async runner.
        # Let's try to get data via engine synchronously if possible or just return a widget that fetches on client side.
        # The widget I created: `WorkflowWidget` fetches details if `execution_id` is provided in `definition.data`.
        # So I can just return the structure with execution_id and let frontend fetch!
        # Plan says: "Fetch workflow execution details using workflow engine... Return widget definition... with execution data"
        # If I can let frontend fetch, that's safer for sync/async issues. 
        # However, listing it in `UI_WIDGET_TOOLS` suggests it should be a tool the agent calls.
        
        # I'll return the widget definition with just execution_id, and let the frontend compoonent do the heavy lifting.
        # This avoids async complexity in the tool definition.
        
        return {
            "type": "workflow",
            "title": "Workflow Status",
            "data": {
                "execution_id": execution_id
            },
            "dismissible": True,
            "expandable": True
        }
    except Exception as e:
        logger.error(f"Error creating workflow widget: {e}")
        return {
            "type": "workflow",
            "title": "Workflow Status (Error)",
            "data": {
                "execution_id": execution_id,
                "error": str(e)
            },
            "dismissible": True
        }

@agent_tool
def create_initiative_dashboard_widget(initiatives: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Creates a dashboard widget to track strategic initiatives.
    
    Args:
        initiatives: List of initiatives with name, status, progress, owner, and optional dueDate.
    """
    processed_initiatives = []
    metrics = {
        "total": len(initiatives),
        "completed": 0,
        "in_progress": 0,
        "blocked": 0
    }
    
    for init in initiatives:
        status = init.get("status", "not_started")
        if status == "completed": metrics["completed"] += 1
        elif status == "in_progress": metrics["in_progress"] += 1
        elif status == "blocked": metrics["blocked"] += 1
        
        processed_initiatives.append({
            "id": init.get("id", f"init-{random.randint(1000,9999)}"),
            "name": init.get("name", "Unnamed Initiative"),
            "status": status,
            "progress": init.get("progress", 0),
            "owner": init.get("owner", "Unassigned"),
            "dueDate": init.get("dueDate")
        })
        
    return {
        "type": "initiative_dashboard",
        "title": "Strategic Initiatives",
        "data": {
            "initiatives": processed_initiatives,
            "metrics": metrics
        },
        "dismissible": True,
        "expandable": True
    }

@agent_tool
def create_revenue_chart_widget(periods: List[str], values: List[float], currency: str = "USD") -> Dict[str, Any]:
    """Creates a revenue chart widget.
    
    Args:
        periods: List of time period labels (e.g., ["Jan", "Feb"])
        values: List of revenue values corresponding to periods
        currency: Currency code (default: USD)
    """
    if not values:
        return {"type": "revenue_chart", "data": {"error": "No data provided"}}
        
    current_revenue = values[-1]
    prev_revenue = values[-2] if len(values) > 1 else current_revenue
    change = current_revenue - prev_revenue
    change_percent = (change / prev_revenue * 100) if prev_revenue else 0
    
    return {
        "type": "revenue_chart",
        "title": "Revenue Overview",
        "data": {
            "periods": periods,
            "values": values,
            "currency": currency,
            "currentPeriod": {
                "revenue": current_revenue,
                "change": change,
                "changePercent": round(change_percent, 1)
            }
        },
        "dismissible": True,
        "expandable": True
    }

@agent_tool
def create_product_launch_widget(milestones: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Creates a product launch tracking widget.
    
    Args:
        milestones: List of milestones with name, date, and status.
    """
    # Determine overall status
    statuses = [m.get("status") for m in milestones]
    overall_status = "on_track"
    if "delayed" in statuses:
        overall_status = "delayed"
    elif "pending" in statuses and "completed" not in statuses:
        overall_status = "at_risk"
        
    return {
        "type": "product_launch",
        "title": "Product Launch Tracker",
        "data": {
            "milestones": milestones,
            "status": overall_status
        },
        "dismissible": True,
        "expandable": True
    }

@agent_tool
def create_kanban_board_widget(columns: List[Dict[str, str]], cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Creates a Kanban board widget.
    
    Args:
        columns: List of columns with id and title
        cards: List of cards with id, columnId, title, description, tags
    """
    return {
        "type": "kanban_board",
        "title": "Project Board",
        "data": {
            "columns": columns,
            "cards": cards
        },
        "dismissible": True,
        "expandable": True
    }

@agent_tool
def create_workflow_builder_widget(nodes: List[Dict[str, Any]] = None, edges: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Creates a workflow builder widget.
    
    Args:
        nodes: Optional list of workflow nodes
        edges: Optional list of workflow edges
    """
    return {
        "type": "workflow_builder",
        "title": "Workflow Builder",
        "data": {
            "nodes": nodes or [],
            "edges": edges or []
        },
        "dismissible": True,
        "expandable": True
    }

@agent_tool
def create_morning_briefing_widget(
    greeting: str, 
    pending_approvals: List[Dict[str, Any]], 
    online_agents: int,
    system_status: str
) -> Dict[str, Any]:
    """Creates a morning briefing widget with system status and approvals."""
    return {
        "type": "morning_briefing",
        "title": "Morning Briefing",
        "data": {
            "greeting": greeting,
            "pending_approvals": pending_approvals,
            "online_agents": online_agents,
            "system_status": system_status
        },
        "dismissible": True,
        "expandable": False # Briefings are usually compact
    }

@agent_tool
def create_boardroom_widget(
    topic: str,
    transcript: List[Dict[str, str]],
    verdict: str
) -> Dict[str, Any]:
    """Creates a boardroom discussion widget."""
    return {
        "type": "boardroom",
        "title": "Boardroom Session",
        "data": {
            "topic": topic,
            "transcript": transcript,
            "verdict": verdict
        },
        "dismissible": True,
        "expandable": True
    }

@agent_tool
def create_suggested_workflows_widget(suggestions: List[Dict[str, str]]) -> Dict[str, Any]:
    """Creates a widget for AI-suggested workflows."""
    return {
        "type": "suggested_workflows",
        "title": "Suggested Workflows",
        "data": {
            "suggestions": suggestions
        },
        "dismissible": True,
        "expandable": True
    }

@agent_tool
def create_form_widget(fields: List[Dict[str, Any]], submit_label: str = "Submit") -> Dict[str, Any]:
    """Creates a form input widget.
    
    Args:
        fields: List of field definitions (name, label, type, required?, options?)
        submit_label: Label for the submit button
    """
    return {
        "type": "form",
        "title": "Input Form",
        "data": {
            "fields": fields,
            "submitLabel": submit_label
        },
        "dismissible": True,
        "expandable": False
    }

@agent_tool
def create_table_widget(
    columns: List[Dict[str, Any]], 
    rows: List[Dict[str, Any]], 
    title: str = "Data Table",
    actions: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Creates a data table widget.
    
    Args:
        columns: List of column definitions
        rows: List of data rows
        title: Title of the table
        actions: Optional list of row actions
    """
    return {
        "type": "table",
        "title": title,
        "data": {
            "columns": columns,
            "rows": rows,
            "actions": actions
        },
        "dismissible": True,
        "expandable": True
    }

@agent_tool
def create_calendar_widget(
    events: List[Dict[str, Any]], 
    view: str = "month"
) -> Dict[str, Any]:
    """Creates a calendar widget.
    
    Args:
        events: List of calendar events
        view: Initial view ('month', 'week', 'day')
    """
    return {
        "type": "calendar",
        "title": "Calendar",
        "data": {
            "events": events,
            "view": view
        },
        "dismissible": True,
        "expandable": True
    }

UI_WIDGET_TOOLS = [
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
    display_workflow
]
