from typing import List, Dict, Any
import json
import random
from app.agents.tools.base import agent_tool
import logging

logger = logging.getLogger(__name__)


def _parse_json_param(value, param_name: str = "param"):
    """Parse a JSON string parameter into a Python object.
    
    Gemini API cannot handle Dict types in tool schemas (rejects
    additionalProperties). Tool parameters that need structured data
    accept JSON strings instead and use this helper to parse them.
    """
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse JSON for param '{param_name}': {value[:100]}")
            return []
    return value  # Already parsed (e.g., list/dict)

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
def create_initiative_dashboard_widget(initiatives: str) -> Dict[str, Any]:
    """Creates a dashboard widget to track strategic initiatives.
    
    Args:
        initiatives: JSON array of initiatives. Each item should have: name, status, progress (0-100), owner, and optional dueDate.
            Example: '[{"name": "Q1 Launch", "status": "in_progress", "progress": 60, "owner": "Alice"}]'
    """
    initiatives = _parse_json_param(initiatives, "initiatives")
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
            "name": init.get("name", init.get("title", "Unnamed Initiative")),
            "title": init.get("title"),
            "status": status,
            "progress": init.get("progress", 0),
            "phase": init.get("phase"),
            "phaseProgress": init.get("phase_progress", init.get("phaseProgress")),
            "owner": init.get("owner", "Unassigned"),
            "dueDate": init.get("dueDate"),
            "workflow_execution_id": init.get("workflow_execution_id"),
            "goal": init.get("goal"),
            "currentPhase": init.get("current_phase", init.get("currentPhase")),
            "successCriteria": init.get("success_criteria", init.get("successCriteria")),
            "primaryWorkflow": init.get("primary_workflow", init.get("primaryWorkflow")),
            "deliverables": init.get("deliverables"),
            "evidence": init.get("evidence"),
            "blockers": init.get("blockers"),
            "nextActions": init.get("next_actions", init.get("nextActions")),
            "trustSummary": init.get("trust_summary", init.get("trustSummary")),
            "verificationStatus": init.get("verification_status", init.get("verificationStatus")),
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
def create_product_launch_widget(milestones: str) -> Dict[str, Any]:
    """Creates a product launch tracking widget.
    
    Args:
        milestones: JSON array of milestones. Each item should have: name, date, and status.
            Example: '[{"name": "Beta Launch", "date": "2026-03-01", "status": "completed"}]'
    """
    milestones = _parse_json_param(milestones, "milestones")
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
def create_kanban_board_widget(columns: str, cards: str) -> Dict[str, Any]:
    """Creates a Kanban board widget.
    
    Args:
        columns: JSON array of columns. Each item should have: id and title.
            Example: '[{"id": "todo", "title": "To Do"}, {"id": "done", "title": "Done"}]'
        cards: JSON array of cards. Each item should have: id, columnId, title, description, tags.
            Example: '[{"id": "1", "columnId": "todo", "title": "Task 1", "description": "Details", "tags": ["urgent"]}]'
    """
    columns = _parse_json_param(columns, "columns")
    cards = _parse_json_param(cards, "cards")
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
def create_workflow_builder_widget(nodes: str = "[]", edges: str = "[]") -> Dict[str, Any]:
    """Creates a workflow builder widget.

    Args:
        nodes: JSON array of workflow nodes. Accepts either `data.label` or legacy top-level `label`.
        edges: JSON array of workflow edges. Accepts optional `id`; one is generated if omitted.
    """
    raw_nodes = _parse_json_param(nodes, "nodes") or []
    raw_edges = _parse_json_param(edges, "edges") or []

    processed_nodes = []
    for index, node in enumerate(raw_nodes):
        if not isinstance(node, dict):
            continue
        node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
        position = node.get("position") if isinstance(node.get("position"), dict) else {}
        label = node_data.get("label") or node.get("label") or f"Step {index + 1}"
        processed_nodes.append({
            "id": node.get("id", f"node-{index + 1}"),
            "position": {
                "x": position.get("x", index * 220),
                "y": position.get("y", 0),
            },
            "data": {"label": label},
            "style": node.get("style"),
        })

    processed_edges = []
    for index, edge in enumerate(raw_edges):
        if not isinstance(edge, dict):
            continue
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        processed_edges.append({
            "id": edge.get("id", f"edge-{source}-{target}-{index + 1}"),
            "source": source,
            "target": target,
            "animated": edge.get("animated"),
            "style": edge.get("style"),
        })

    return {
        "type": "workflow_builder",
        "title": "Workflow Builder",
        "data": {
            "nodes": processed_nodes,
            "edges": processed_edges,
        },
        "dismissible": True,
        "expandable": True,
    }

@agent_tool
def create_morning_briefing_widget(
    greeting: str,
    pending_approvals: str,
    online_agents: int,
    system_status: str
) -> Dict[str, Any]:
    """Creates a morning briefing widget with system status and approvals.

    Args:
        greeting: Greeting message for the user.
        pending_approvals: JSON array of pending approvals. Each item should have: id, action_type, created_at, and token.
        online_agents: Number of online agents.
        system_status: Current system status string (e.g., 'healthy', 'degraded').
    """
    raw_pending_approvals = _parse_json_param(pending_approvals, "pending_approvals") or []
    normalized_pending_approvals = []
    for index, item in enumerate(raw_pending_approvals):
        if not isinstance(item, dict):
            continue
        normalized_pending_approvals.append({
            "id": item.get("id", f"approval-{index + 1}"),
            "action_type": item.get("action_type") or item.get("title") or "Approval Required",
            "created_at": item.get("created_at") or "",
            "token": item.get("token") or item.get("public_token") or "",
        })
    return {
        "type": "morning_briefing",
        "title": "Morning Briefing",
        "data": {
            "greeting": greeting,
            "pending_approvals": normalized_pending_approvals,
            "online_agents": online_agents,
            "system_status": system_status,
        },
        "dismissible": True,
        "expandable": False,
    }

@agent_tool
def create_boardroom_widget(
    topic: str,
    transcript: str,
    verdict: str
) -> Dict[str, Any]:
    """Creates a boardroom discussion widget.

    Args:
        topic: The discussion topic.
        transcript: JSON array of transcript entries. Each item should have: speaker and content (or legacy text).
        verdict: The final decision or verdict from the discussion.
    """
    raw_transcript = _parse_json_param(transcript, "transcript") or []
    normalized_transcript = []
    for item in raw_transcript:
        if not isinstance(item, dict):
            continue
        normalized_transcript.append({
            "speaker": item.get("speaker", "Agent"),
            "content": item.get("content") or item.get("text") or "",
            "sentiment": item.get("sentiment", "neutral"),
        })
    return {
        "type": "boardroom",
        "title": "Boardroom Session",
        "data": {
            "topic": topic,
            "transcript": normalized_transcript,
            "verdict": verdict,
        },
        "dismissible": True,
        "expandable": True,
    }

@agent_tool
def create_suggested_workflows_widget(suggestions: str) -> Dict[str, Any]:
    """Creates a widget for AI-suggested workflows.

    Args:
        suggestions: JSON array of workflow suggestions. Each item should have: id, pattern_description, suggested_goal, suggested_context, and status.
    """
    raw_suggestions = _parse_json_param(suggestions, "suggestions") or []
    normalized_suggestions = []
    for index, suggestion in enumerate(raw_suggestions):
        if not isinstance(suggestion, dict):
            continue
        normalized_suggestions.append({
            "id": suggestion.get("id", f"suggestion-{index + 1}"),
            "pattern_description": suggestion.get("pattern_description") or suggestion.get("description") or suggestion.get("name") or "Suggested workflow",
            "suggested_goal": suggestion.get("suggested_goal") or suggestion.get("goal") or suggestion.get("name") or "Untitled goal",
            "suggested_context": suggestion.get("suggested_context") or suggestion.get("context") or suggestion.get("description") or "",
            "status": suggestion.get("status", "suggested"),
        })
    return {
        "type": "suggested_workflows",
        "title": "Suggested Workflows",
        "data": {
            "suggestions": normalized_suggestions,
        },
        "dismissible": True,
        "expandable": True,
    }

@agent_tool
def create_form_widget(fields: str, submit_label: str = "Submit") -> Dict[str, Any]:
    """Creates a form input widget.
    
    Args:
        fields: JSON array of field definitions. Each item should have: name, label, type (text/email/select/textarea), and optional required (boolean) and options (for select).
            Example: '[{"name": "email", "label": "Email", "type": "email", "required": true}]'
        submit_label: Label for the submit button
    """
    fields = _parse_json_param(fields, "fields")
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
    columns: str, 
    rows: str, 
    title: str = "Data Table",
    actions: str = "[]"
) -> Dict[str, Any]:
    """Creates a data table widget.
    
    Args:
        columns: JSON array of column definitions. Each item should have: key, label, and optional sortable (boolean).
            Example: '[{"key": "name", "label": "Name"}, {"key": "email", "label": "Email"}]'
        rows: JSON array of data rows. Each item is an object with keys matching column keys.
            Example: '[{"name": "Alice", "email": "alice@co.com"}]'
        title: Title of the table
        actions: JSON array of row actions. Each item should have: label and action.
            Example: '[{"label": "Edit", "action": "edit"}]'
    """
    columns = _parse_json_param(columns, "columns")
    rows = _parse_json_param(rows, "rows")
    actions = _parse_json_param(actions, "actions")
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
    events: str, 
    view: str = "month"
) -> Dict[str, Any]:
    """Creates a calendar widget.
    
    Args:
        events: JSON array of calendar events. Each item should have: title, start (ISO date), end (ISO date), and optional color.
            Example: '[{"title": "Team Meeting", "start": "2026-02-10T10:00:00", "end": "2026-02-10T11:00:00"}]'
        view: Initial view ('month', 'week', 'day')
    """
    events = _parse_json_param(events, "events")
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

def display_workflow_observability() -> Dict[str, Any]:
    """Displays a workflow pipeline health widget showing execution stats,
    success/failure rates, top failing tools, and recent failures.

    Use this when users ask about workflow health, pipeline status, or
    want to see workflow execution metrics and failure analysis.
    The widget auto-fetches live stats from the backend.
    """
    return {
        "type": "workflow_observability",
        "title": "Pipeline Health",
        "data": {},
        "dismissible": True,
        "expandable": True,
    }


@agent_tool
def display_workflow_timeline(execution_id: str) -> Dict[str, Any]:
    """Displays a visual timeline for a specific workflow execution, showing
    each step's duration as a horizontal bar chart grouped by phase.

    Use this when the user wants to see how long each step took in a workflow,
    visualize parallel execution, or inspect step-level failures.
    Requires the execution_id of a running or completed workflow.

    Args:
        execution_id: The UUID of the workflow execution to visualize.
    """
    return {
        "type": "workflow_timeline",
        "title": "Execution Timeline",
        "data": {"execution_id": execution_id},
        "dismissible": True,
        "expandable": True,
    }


@agent_tool
def create_campaign_hub_widget(
    campaign_name: str = "",
    campaign_status: str = "active",
    stats: str = "[]",
    pipeline_items: str = "[]",
    pipeline_phase: str = "",
    social_accounts: str = "[]",
    competitors: str = "[]",
    news_feed: str = "[]",
    top_posts: str = "[]",
    research_summary: str = "",
    analytics_period: str = "",
    target_audience: str = "",
    channels: str = "[]",
    impressions: int = 0,
    clicks: int = 0,
    conversions: int = 0,
    ctr: float = 0.0,
) -> Dict[str, Any]:
    """Creates a marketing campaign hub widget with analytics, content pipeline, competitor tracking, and industry news.

    Args:
        campaign_name: Name of the active campaign.
        campaign_status: Campaign status (draft, active, paused, completed).
        stats: JSON array of quick stats. Each: label, value, change (optional), trend ('up'/'down'/'flat').
        pipeline_items: JSON array of content pipeline items. Each: type (video/image/blog/social/email), title, status (draft/in_review/approved/published), platform (optional).
        pipeline_phase: Current pipeline phase label.
        social_accounts: JSON array of connected social accounts. Each: platform, connected (bool), last_post (optional).
        competitors: JSON array of competitor entries. Each: handle, platform, name (optional), followers (optional), engagement_rate (optional), posting_frequency (optional), growth_trend ('up'/'down'/'flat'), recent_posts (optional).
        news_feed: JSON array of industry news items. Each: id, headline, source, published_at, summary, topic (optional), url (optional).
        top_posts: JSON array of top performing posts. Each: title, platform (optional), impressions (optional), engagement_rate (optional), published_at (optional).
        research_summary: Market intelligence summary text.
        analytics_period: Date range label for the analytics (e.g., 'Mar 1 - Mar 15, 2026').
        target_audience: Target audience description.
        channels: JSON array of channel names (e.g., '["instagram", "linkedin"]').
        impressions: Total impressions count.
        clicks: Total clicks count.
        conversions: Total conversions count.
        ctr: Click-through rate percentage.
    """
    parsed_stats = _parse_json_param(stats, "stats") or []
    parsed_pipeline = _parse_json_param(pipeline_items, "pipeline_items") or []
    parsed_social = _parse_json_param(social_accounts, "social_accounts") or []
    parsed_competitors = _parse_json_param(competitors, "competitors") or []
    parsed_news = _parse_json_param(news_feed, "news_feed") or []
    parsed_top_posts = _parse_json_param(top_posts, "top_posts") or []
    parsed_channels = _parse_json_param(channels, "channels") or []

    data: Dict[str, Any] = {}

    # Campaign overview
    if campaign_name:
        campaign_data: Dict[str, Any] = {
            "id": f"campaign-{random.randint(1000, 9999)}",
            "name": campaign_name,
            "status": campaign_status,
        }
        if target_audience:
            campaign_data["target_audience"] = target_audience
        if parsed_channels:
            campaign_data["channels"] = parsed_channels
        if impressions or clicks or conversions or ctr:
            campaign_data["metrics"] = {
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "ctr": ctr,
            }
        data["campaign"] = campaign_data

    # Quick stats
    if parsed_stats:
        data["stats"] = parsed_stats

    # Content pipeline
    if parsed_pipeline:
        data["content_pipeline"] = {
            "phase": pipeline_phase or "Production",
            "items": parsed_pipeline,
        }

    # Social accounts
    if parsed_social:
        data["social_accounts"] = parsed_social

    # Competitor tracker
    if parsed_competitors:
        data["competitors"] = parsed_competitors

    # Industry news feed
    if parsed_news:
        # Ensure each news item has an id
        for i, item in enumerate(parsed_news):
            if isinstance(item, dict) and "id" not in item:
                item["id"] = f"news-{i + 1}"
        data["news_feed"] = parsed_news

    # Top performing posts
    if parsed_top_posts:
        data["top_posts"] = parsed_top_posts

    # Research summary
    if research_summary:
        data["research_summary"] = research_summary

    # Analytics period
    if analytics_period:
        data["analytics_period"] = analytics_period

    return {
        "type": "campaign_hub",
        "title": "Campaign Hub",
        "data": data,
        "dismissible": True,
        "expandable": True,
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
    create_campaign_hub_widget,
    display_workflow,
    display_workflow_observability,
    display_workflow_timeline,
]


