"""MCP Setup Wizard Tools - Agent tools for helping users configure integrations.

These tools allow AI agents to guide users through setting up MCP integrations
in a conversational manner, making it easy for non-technical users.
"""

import asyncio
import re
from typing import Any

import httpx

from app.mcp.user_config import (
    INTEGRATION_TEMPLATES,
    get_user_config_service,
)


def mcp_list_available_integrations(
    category: str | None = None,
) -> dict[str, Any]:
    """List all available MCP integrations that users can set up.

    Returns a list of integration templates with their requirements.
    Use this to show users what integrations are available.

    Args:
        category: Optional filter by category (database, email, communication, etc.)

    Returns:
        Dictionary with list of available integrations and their details.
    """
    service = get_user_config_service()
    templates = service.get_templates()

    if category:
        templates = [t for t in templates if t.category == category]

    return {
        "success": True,
        "integrations": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "docs_url": t.docs_url,
            }
            for t in templates
        ],
        "categories": list(set(t.category for t in service.get_templates())),
    }


def mcp_get_integration_requirements(
    integration_type: str,
) -> dict[str, Any]:
    """Get the required and optional fields for setting up an integration.

    Use this to know what information to ask the user for.

    Args:
        integration_type: The type of integration (e.g., 'supabase', 'resend', 'custom')

    Returns:
        Dictionary with required fields, optional fields, and documentation URL.
    """
    template = INTEGRATION_TEMPLATES.get(integration_type)

    if not template:
        return {
            "success": False,
            "error": f"Unknown integration type: {integration_type}",
            "available_types": list(INTEGRATION_TEMPLATES.keys()),
        }

    return {
        "success": True,
        "integration_type": integration_type,
        "name": template.name,
        "description": template.description,
        "required_fields": template.required_fields,
        "optional_fields": template.optional_fields,
        "docs_url": template.docs_url,
        "setup_instructions": _get_setup_instructions(integration_type),
    }


def _get_setup_instructions(integration_type: str) -> str:
    """Get human-readable setup instructions for an integration."""
    instructions = {
        "supabase": """
To set up Supabase:
1. Go to your Supabase dashboard (https://supabase.com/dashboard)
2. Select your project
3. Go to Settings → API
4. Copy the Project URL, anon key, and service_role key
""",
        "resend": """
To set up Resend:
1. Go to Resend dashboard (https://resend.com)
2. Click on API Keys in the sidebar
3. Create a new API key with full access
4. Copy the key (starts with 're_')
""",
        "slack": """
To set up Slack:
1. Go to https://api.slack.com/apps
2. Create a new app or select existing
3. Go to Incoming Webhooks
4. Activate and create a new webhook URL
""",
        "notion": """
To set up Notion:
1. Go to https://www.notion.so/my-integrations
2. Create a new integration
3. Copy the Internal Integration Token
4. Share your database/page with the integration
""",
        "stripe": """
To set up Stripe:
1. Go to https://dashboard.stripe.com/apikeys
2. Copy your Secret key (starts with 'sk_')
3. For webhooks, go to Developers → Webhooks
""",
        "custom": """
For custom integrations:
1. Enter the base URL of the API
2. Provide your API key if required
3. Add any custom headers as JSON if needed
""",
    }
    return instructions.get(
        integration_type, "Please refer to the integration's documentation."
    )


def mcp_validate_api_key(
    integration_type: str,
    field_key: str,
    value: str,
) -> dict[str, Any]:
    """Validate the format of an API key or configuration value.

    Use this to quickly check if a value looks valid before saving.
    This does NOT test the actual connection - use mcp_test_integration for that.

    Args:
        integration_type: The integration type (e.g., 'supabase', 'resend')
        field_key: The field being validated (e.g., 'api_key', 'url')
        value: The value to validate

    Returns:
        Dictionary with validation result and any error messages.
    """
    validators = {
        ("supabase", "url"): (
            r"^https://[a-zA-Z0-9-]+\.supabase\.co$",
            "Supabase URL should be like: https://xxxxx.supabase.co",
        ),
        ("supabase", "anon_key"): (
            r"^eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+$",
            "Supabase anon key should be a JWT token starting with 'eyJ'",
        ),
        ("supabase", "service_role_key"): (
            r"^eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+$",
            "Supabase service role key should be a JWT token starting with 'eyJ'",
        ),
        ("resend", "api_key"): (
            r"^re_[a-zA-Z0-9_]+$",
            "Resend API key should start with 're_'",
        ),
        ("slack", "webhook_url"): (
            r"^https://hooks\.slack\.com/services/",
            "Slack webhook URL should start with 'https://hooks.slack.com/services/'",
        ),
        ("notion", "api_key"): (
            r"^(secret_|ntn_)[a-zA-Z0-9]+$",
            "Notion token should start with 'secret_' or 'ntn_'",
        ),
        ("stripe", "secret_key"): (
            r"^sk_(live|test)_[a-zA-Z0-9]+$",
            "Stripe secret key should start with 'sk_live_' or 'sk_test_'",
        ),
        ("openai", "api_key"): (
            r"^sk-[a-zA-Z0-9-]+$",
            "OpenAI API key should start with 'sk-'",
        ),
    }

    key = (integration_type, field_key)

    if key in validators:
        pattern, message = validators[key]
        if re.match(pattern, value):
            return {"success": True, "valid": True, "message": "Format looks valid"}
        else:
            return {"success": True, "valid": False, "message": message}

    # For unknown fields, just check it's not empty
    if value and len(value) > 0:
        return {"success": True, "valid": True, "message": "Value provided"}
    else:
        return {"success": True, "valid": False, "message": "Value cannot be empty"}


async def _test_supabase(config: dict[str, Any]) -> dict[str, Any]:
    """Test Supabase connection."""
    url = config.get("url", "").rstrip("/")
    key = config.get("service_role_key") or config.get("anon_key")

    if not url or not key:
        return {"success": False, "error": "Missing URL or API key"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{url}/rest/v1/",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                },
                timeout=10.0,
            )
            if response.status_code in (200, 204):
                return {
                    "success": True,
                    "message": "Connected to Supabase successfully",
                }
            else:
                return {
                    "success": False,
                    "error": f"Connection failed: {response.status_code}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


async def _test_resend(config: dict[str, Any]) -> dict[str, Any]:
    """Test Resend connection."""
    api_key = config.get("api_key")
    if not api_key:
        return {"success": False, "error": "Missing API key"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.resend.com/domains",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                return {"success": True, "message": "Connected to Resend successfully"}
            elif response.status_code == 401:
                return {"success": False, "error": "Invalid API key"}
            else:
                return {
                    "success": False,
                    "error": f"Connection failed: {response.status_code}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


async def _test_slack(config: dict[str, Any]) -> dict[str, Any]:
    """Test Slack webhook."""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return {"success": False, "error": "Missing webhook URL"}

    async with httpx.AsyncClient() as client:
        try:
            # Send a test message
            response = await client.post(
                webhook_url,
                json={"text": "🔗 Pikar AI integration test - connection successful!"},
                timeout=10.0,
            )
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Slack webhook working - check your channel for the test message",
                }
            else:
                return {"success": False, "error": f"Webhook failed: {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def _test_notion(config: dict[str, Any]) -> dict[str, Any]:
    """Test Notion connection."""
    api_key = config.get("api_key")
    if not api_key:
        return {"success": False, "error": "Missing API key"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.notion.com/v1/users/me",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Notion-Version": "2022-06-28",
                },
                timeout=10.0,
            )
            if response.status_code == 200:
                return {"success": True, "message": "Connected to Notion successfully"}
            elif response.status_code == 401:
                return {"success": False, "error": "Invalid integration token"}
            else:
                return {
                    "success": False,
                    "error": f"Connection failed: {response.status_code}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


async def _test_generic(config: dict[str, Any]) -> dict[str, Any]:
    """Test a generic/custom API connection."""
    base_url = config.get("base_url")
    api_key = config.get("api_key")
    headers = config.get("headers", {})

    if not base_url:
        return {"success": False, "error": "Missing base URL"}

    if isinstance(headers, str):
        import json

        try:
            headers = json.loads(headers)
        except (json.JSONDecodeError, ValueError):
            headers = {}

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                base_url,
                headers=headers,
                timeout=10.0,
            )
            if response.status_code < 400:
                return {
                    "success": True,
                    "message": f"Connected successfully (status: {response.status_code})",
                }
            else:
                return {
                    "success": False,
                    "error": f"Connection failed: {response.status_code}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


def mcp_test_integration(
    integration_type: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Test if an integration works with the provided credentials.

    Actually connects to the service to verify the credentials work.
    Use this after collecting all required fields from the user.

    Args:
        integration_type: The integration type (e.g., 'supabase', 'resend')
        config: Dictionary of configuration values (keys match required_fields)

    Returns:
        Dictionary with test result, success/failure message.
    """
    testers = {
        "supabase": _test_supabase,
        "resend": _test_resend,
        "slack": _test_slack,
        "notion": _test_notion,
        "custom": _test_generic,
    }

    tester = testers.get(integration_type, _test_generic)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, tester(config))
                result = future.result(timeout=30)
        else:
            result = loop.run_until_complete(tester(config))

        return {
            "success": result.get("success", False),
            "integration_type": integration_type,
            "message": result.get("message") or result.get("error"),
            "can_activate": result.get("success", False),
        }
    except Exception as e:
        return {
            "success": False,
            "integration_type": integration_type,
            "message": f"Test failed: {e!s}",
            "can_activate": False,
        }


def mcp_save_integration(
    user_id: str,
    integration_type: str,
    config: dict[str, Any],
    display_name: str | None = None,
) -> dict[str, Any]:
    """Save a user's integration configuration.

    Encrypts and stores the configuration. The integration will be inactive
    until tested and activated.

    Args:
        user_id: The user's ID
        integration_type: The integration type (e.g., 'supabase', 'resend')
        config: Dictionary of configuration values
        display_name: Optional custom name for this integration

    Returns:
        Dictionary with save result and integration ID.
    """
    service = get_user_config_service()
    result = service.save_integration(
        user_id=user_id,
        integration_type=integration_type,
        config=config,
        display_name=display_name,
    )
    return result


def mcp_activate_integration(
    user_id: str,
    integration_id: str,
) -> dict[str, Any]:
    """Activate a configured integration after testing.

    The integration must have passed testing before it can be activated.
    Once activated, agents can use this integration for the user.

    Args:
        user_id: The user's ID (for verification)
        integration_id: The integration's unique ID

    Returns:
        Dictionary with activation result.
    """
    service = get_user_config_service()
    success = service.activate_integration(integration_id)

    if success:
        return {
            "success": True,
            "message": "Integration activated! It's now ready to use.",
        }
    else:
        return {
            "success": False,
            "message": "Could not activate. Make sure the integration passed testing first.",
        }


def mcp_get_user_integrations(
    user_id: str,
) -> dict[str, Any]:
    """Get all configured integrations for a user.

    Returns both active and inactive integrations with their status.

    Args:
        user_id: The user's ID

    Returns:
        Dictionary with list of user's integrations.
    """
    service = get_user_config_service()
    integrations = service.get_user_integrations(user_id)

    return {
        "success": True,
        "integrations": [
            {
                "id": i.id,
                "type": i.integration_type,
                "display_name": i.display_name,
                "is_active": i.is_active,
                "test_status": i.test_status,
                "last_tested_at": str(i.last_tested_at) if i.last_tested_at else None,
            }
            for i in integrations
        ],
        "active_count": sum(1 for i in integrations if i.is_active),
        "total_count": len(integrations),
    }


# Export all tools
MCP_SETUP_TOOLS = [
    mcp_list_available_integrations,
    mcp_get_integration_requirements,
    mcp_validate_api_key,
    mcp_test_integration,
    mcp_save_integration,
    mcp_activate_integration,
    mcp_get_user_integrations,
]
