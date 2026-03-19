"""Integration Setup Guide Tools.

ADK-compatible tools that let the AI agent guide non-technical users
through configuring the external API keys and OAuth connections needed
to run their workflows and journeys.
"""

from typing import Any, Dict, List, Optional


def check_integration_status(
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Check which integrations are configured and which are missing.

    Returns the status of every external service the system can use.
    Use this at the start of a conversation or when a user wants to
    run a workflow that might need external APIs.

    Args:
        user_id: The user's ID (for checking OAuth connections).

    Returns:
        Dictionary with per-integration status (configured/missing),
        plus a summary of what workflows are unlocked vs blocked.
    """
    from app.mcp.config import get_mcp_config
    from app.workflows.contract_defaults import INTEGRATION_SETUP_GUIDE

    config = get_mcp_config()

    statuses = {
        "tavily": {
            "configured": config.is_tavily_configured(),
            **INTEGRATION_SETUP_GUIDE.get("tavily", {}),
        },
        "firecrawl": {
            "configured": config.is_firecrawl_configured(),
            **INTEGRATION_SETUP_GUIDE.get("firecrawl", {}),
        },
        "stitch": {
            "configured": config.is_stitch_configured(),
            **INTEGRATION_SETUP_GUIDE.get("stitch", {}),
        },
        "resend": {
            "configured": config.is_email_configured(),
            **INTEGRATION_SETUP_GUIDE.get("resend", {}),
        },
        "hubspot": {
            "configured": config.is_crm_configured(),
            **INTEGRATION_SETUP_GUIDE.get("hubspot", {}),
        },
        "google_seo": {
            "configured": config.is_google_seo_configured(),
            **INTEGRATION_SETUP_GUIDE.get("google_seo", {}),
        },
        "google_analytics": {
            "configured": config.is_google_analytics_configured(),
            **INTEGRATION_SETUP_GUIDE.get("google_analytics", {}),
        },
        "google_ai": {
            "configured": bool(
                __import__("os").environ.get("GOOGLE_API_KEY")
                or __import__("os").environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            ),
            **INTEGRATION_SETUP_GUIDE.get("google_ai", {}),
        },
    }

    # Check social OAuth connections if user_id provided
    social_status = {"configured": False, "platforms": []}
    if user_id:
        try:
            from app.social.connector import get_social_connector
            connector = get_social_connector()
            connections = connector.list_connections(user_id)
            active = [c["platform"] for c in connections if c.get("status") == "active"]
            social_status = {
                "configured": len(active) > 0,
                "platforms": active,
                **INTEGRATION_SETUP_GUIDE.get("social_oauth", {}),
            }
        except Exception:
            social_status = {
                "configured": False,
                "platforms": [],
                **INTEGRATION_SETUP_GUIDE.get("social_oauth", {}),
            }

    statuses["social_oauth"] = social_status

    configured_count = sum(1 for s in statuses.values() if s.get("configured"))
    total_count = len(statuses)

    return {
        "success": True,
        "integrations": statuses,
        "summary": {
            "configured": configured_count,
            "total": total_count,
            "missing": total_count - configured_count,
            "missing_names": [k for k, v in statuses.items() if not v.get("configured")],
        },
    }


def get_setup_guide(
    integration_id: str,
) -> Dict[str, Any]:
    """Get step-by-step setup instructions for a specific integration.

    Returns detailed instructions that you can walk the user through,
    including where to sign up, how to get the API key, and where to
    paste it. Designed for non-technical users.

    Args:
        integration_id: The integration to get setup help for. Options:
            tavily, firecrawl, stitch, resend, hubspot,
            google_seo, google_analytics, google_ai, social_oauth.

    Returns:
        Dictionary with name, description, setup_steps, setup_url,
        free_tier info, and which workflows this integration unlocks.
    """
    from app.workflows.contract_defaults import INTEGRATION_SETUP_GUIDE

    guide = INTEGRATION_SETUP_GUIDE.get(integration_id)
    if not guide:
        available = list(INTEGRATION_SETUP_GUIDE.keys())
        return {
            "error": f"Unknown integration '{integration_id}'. Available: {available}",
        }

    return {
        "success": True,
        "integration_id": integration_id,
        **guide,
    }


def get_workflow_requirements(
    workflow_name: str,
) -> Dict[str, Any]:
    """Check what integrations a specific workflow needs to run.

    Use this before starting a workflow to tell the user what they
    need to set up. Returns the list of required integrations, their
    status (configured/missing), and setup links for anything missing.

    Args:
        workflow_name: The workflow template name (e.g. "Lead Generation Workflow",
                       "Content Creation Workflow", "SEO Optimization Audit").

    Returns:
        Dictionary with required integrations, their status, and
        whether the workflow is ready to run.
    """
    from app.mcp.config import get_mcp_config
    from app.workflows.contract_defaults import (
        TOOL_REQUIRED_INTEGRATIONS,
        INTEGRATION_SETUP_GUIDE,
    )

    # Load the workflow YAML to find its tools
    import yaml
    from pathlib import Path

    definitions_dir = Path(__file__).resolve().parents[2] / "workflows" / "definitions"
    workflow_tools = []

    for yaml_file in definitions_dir.glob("*.yaml"):
        try:
            parsed = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if parsed.get("name") == workflow_name:
            for phase in parsed.get("phases", []):
                for step in phase.get("steps", []):
                    tool = step.get("tool")
                    if tool:
                        workflow_tools.append(tool)
            break

    if not workflow_tools:
        return {
            "error": f"Workflow '{workflow_name}' not found.",
            "hint": "Check the exact name — it must match the YAML definition.",
        }

    # Collect all required integrations for this workflow's tools
    required = set()
    for tool in workflow_tools:
        integrations = TOOL_REQUIRED_INTEGRATIONS.get(tool, [])
        required.update(integrations)

    # Check status of each
    config = get_mcp_config()
    config_checks = {
        "tavily": config.is_tavily_configured(),
        "firecrawl": config.is_firecrawl_configured(),
        "stitch": config.is_stitch_configured(),
        "resend": config.is_email_configured(),
        "hubspot": config.is_crm_configured(),
        "google_seo": config.is_google_seo_configured(),
        "google_analytics": config.is_google_analytics_configured(),
        "google_ai": bool(
            __import__("os").environ.get("GOOGLE_API_KEY")
            or __import__("os").environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        ),
        "social_oauth": False,  # Requires user-level check
    }

    integration_details = []
    all_ready = True
    for integration_id in sorted(required):
        configured = config_checks.get(integration_id, False)
        guide = INTEGRATION_SETUP_GUIDE.get(integration_id, {})
        if not configured:
            all_ready = False
        integration_details.append({
            "id": integration_id,
            "name": guide.get("name", integration_id),
            "configured": configured,
            "setup_url": guide.get("setup_url", ""),
            "free_tier": guide.get("free_tier", ""),
        })

    return {
        "success": True,
        "workflow_name": workflow_name,
        "tools": workflow_tools,
        "required_integrations": integration_details,
        "ready_to_run": all_ready,
        "missing_count": sum(1 for i in integration_details if not i["configured"]),
        "message": (
            f"'{workflow_name}' is ready to run!"
            if all_ready
            else f"'{workflow_name}' needs {sum(1 for i in integration_details if not i['configured'])} integration(s) configured first."
        ),
    }


INTEGRATION_SETUP_TOOLS = [
    check_integration_status,
    get_setup_guide,
    get_workflow_requirements,
]
