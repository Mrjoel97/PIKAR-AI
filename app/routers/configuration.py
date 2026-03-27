# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Configuration API Router.

Manages user configurations for MCP tools and social media connections.
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.mcp.config import get_mcp_config
from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client
from app.social.connector import get_social_connector

router = APIRouter(prefix="/configuration", tags=["Configuration"])


def _resolve_user_id(current_user_id: str, provided_user_id: str | None = None) -> str:
    if provided_user_id and provided_user_id != current_user_id:
        raise HTTPException(
            status_code=403, detail="Cannot access another user's configuration"
        )
    return current_user_id


# ============================================================================
# Pydantic Models
# ============================================================================


class MCPToolStatus(BaseModel):
    """Status of an MCP tool."""

    id: str
    name: str
    description: str
    configured: bool
    env_var: str | None = None
    docs_url: str | None = None
    is_built_in: bool = False


class BuiltInToolStatus(BaseModel):
    """Status of a built-in tool."""

    id: str
    name: str
    description: str
    is_built_in: bool = True
    configured: bool = False
    status: str = "Bundled in the app"


class SchedulerReadinessStatus(BaseModel):
    """Readiness of scheduled jobs for server-side execution."""

    configuration_ready: bool
    worker_schedule_tick_enabled: bool = True
    secure_endpoints_enabled: bool = True
    deployment_required: bool = True
    status: str
    message: str


class MCPStatusResponse(BaseModel):
    """Response with all MCP tool statuses."""

    built_in_tools: list[BuiltInToolStatus]
    configurable_tools: list[MCPToolStatus]
    scheduler_readiness: SchedulerReadinessStatus


class SocialPlatformStatus(BaseModel):
    """Status of a social media platform connection."""

    platform: str
    display_name: str
    icon: str
    connected: bool
    username: str | None = None
    connected_at: str | None = None
    requires_config: bool
    config_keys: list[str]


class SocialStatusResponse(BaseModel):
    """Response with all social platform statuses."""

    platforms: list[SocialPlatformStatus]


class GoogleWorkspaceStatus(BaseModel):
    """Status of Google Workspace connection."""

    connected: bool
    email: str | None = None
    provider: str | None = None
    features: list[str] = []
    message: str


class SaveConfigRequest(BaseModel):
    """Request to save a configuration value."""

    key: str
    value: str
    user_id: str


class SaveConfigResponse(BaseModel):
    """Response after saving configuration."""

    success: bool
    message: str


class ConnectSocialRequest(BaseModel):
    """Request to initiate social media connection."""

    platform: str
    user_id: str
    redirect_uri: str


class ConnectSocialResponse(BaseModel):
    """Response with OAuth authorization URL."""

    authorization_url: str | None = None
    state: str | None = None
    error: str | None = None


class DisconnectSocialRequest(BaseModel):
    """Request to disconnect social media account."""

    platform: str
    user_id: str


class SessionConfigResponse(BaseModel):
    """Session configuration for frontend."""

    max_concurrent_streams: int = 4
    memory_eviction_minutes: int = 30
    max_active_sessions_in_memory: int = 20


# ============================================================================
# MCP Tool Definitions
# ============================================================================

# Built-in tools (bundled in the app, but still require server-side provider config)
BUILT_IN_TOOLS_INFO = [
    {
        "id": "tavily",
        "name": "Web Search (Tavily)",
        "description": "AI-powered web search - automatically used for research tasks.",
        "is_built_in": True,
    },
    {
        "id": "firecrawl",
        "name": "Web Scraping (Firecrawl)",
        "description": "Content extraction from webpages - automatically used for deep research.",
        "is_built_in": True,
    },
]


def _is_built_in_tool_configured(tool_id: str, config) -> bool:
    if tool_id == "tavily":
        return config.is_tavily_configured()
    if tool_id == "firecrawl":
        return config.is_firecrawl_configured()
    return False


def _built_in_status(tool_id: str, config) -> str:
    if _is_built_in_tool_configured(tool_id, config):
        return "Configured server-side and ready for automatic use"
    return "Bundled in the app, but inactive until its API key is configured"


def _scheduler_readiness(config) -> SchedulerReadinessStatus:
    scheduler_secret_configured = bool(
        (os.environ.get("SCHEDULER_SECRET") or "").strip()
    )

    if scheduler_secret_configured:
        status = "App is ready to be deployed for scheduled jobs"
        message = (
            "Scheduler authentication is configured and the worker can execute saved report schedules. "
            "You still need always-on API and worker services plus an external scheduler for unattended runs."
        )
    else:
        status = "Scheduled jobs need one more configuration step"
        message = (
            "Add SCHEDULER_SECRET in the server environment to secure scheduled endpoints. "
            "The worker-side schedule tick is already wired, but unattended runs still require always-on deployment."
        )

    return SchedulerReadinessStatus(
        configuration_ready=scheduler_secret_configured,
        worker_schedule_tick_enabled=True,
        secure_endpoints_enabled=True,
        deployment_required=True,
        status=status,
        message=message,
    )


# User-configurable MCP tools
# User-configurable MCP tools
MCP_TOOLS_INFO = [
    {
        "id": "stitch",
        "name": "Landing Page Builder (Stitch)",
        "description": "Generate professional landing pages with AI. Creates HTML and React components.",
        "env_var": "STITCH_API_KEY",
        "docs_url": "https://stitch.withgoogle.com/docs",
    },
    {
        "id": "stripe",
        "name": "Payments (Stripe)",
        "description": "Accept payments, create checkout sessions, and manage subscriptions for landing pages.",
        "env_var": "STRIPE_API_KEY",
        "docs_url": "https://stripe.com/docs",
    },
    {
        "id": "canva",
        "name": "Media Creation (Canva)",
        "description": "Create professional graphics, social media posts, and visual content with AI.",
        "env_var": "CANVA_API_KEY",
        "docs_url": "https://www.canva.dev/docs",
    },
    {
        "id": "resend",
        "name": "Email Service (Resend)",
        "description": "Send transactional emails and notifications to users and customers.",
        "env_var": "RESEND_API_KEY",
        "docs_url": "https://resend.com/docs",
    },
    {
        "id": "hubspot",
        "name": "CRM Integration (HubSpot)",
        "description": "Sync contacts, track deals, and manage customer relationships.",
        "env_var": "HUBSPOT_API_KEY",
        "docs_url": "https://developers.hubspot.com/docs",
    },
]


# ============================================================================
# Social Platform Definitions
# ============================================================================

SOCIAL_PLATFORMS_INFO = [
    {
        "platform": "twitter",
        "display_name": "Twitter / X",
        "icon": "twitter",
        "config_keys": ["TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET"],
    },
    {
        "platform": "linkedin",
        "display_name": "LinkedIn",
        "icon": "linkedin",
        "config_keys": ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"],
    },
    {
        "platform": "facebook",
        "display_name": "Facebook",
        "icon": "facebook",
        "config_keys": ["FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"],
    },
    {
        "platform": "instagram",
        "display_name": "Instagram",
        "icon": "instagram",
        "config_keys": ["FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"],
    },
    {
        "platform": "youtube",
        "display_name": "YouTube",
        "icon": "youtube",
        "config_keys": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
    },
    {
        "platform": "tiktok",
        "display_name": "TikTok",
        "icon": "tiktok",
        "config_keys": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"],
    },
]


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/mcp-status", response_model=MCPStatusResponse)
@limiter.limit(get_user_persona_limit)
async def get_mcp_status(request: Request, _user_id: str = Depends(get_current_user_id)):
    """Get status of all MCP tools including built-in and configurable."""
    config = get_mcp_config()

    built_in = []
    for tool_info in BUILT_IN_TOOLS_INFO:
        built_in.append(
            BuiltInToolStatus(
                id=tool_info["id"],
                name=tool_info["name"],
                description=tool_info["description"],
                is_built_in=True,
                configured=_is_built_in_tool_configured(tool_info["id"], config),
                status=_built_in_status(tool_info["id"], config),
            )
        )

    tools = []
    for tool_info in MCP_TOOLS_INFO:
        env_value = os.environ.get(tool_info["env_var"])
        is_configured = bool(env_value and len(env_value) > 0)

        tools.append(
            MCPToolStatus(
                id=tool_info["id"],
                name=tool_info["name"],
                description=tool_info["description"],
                configured=is_configured,
                env_var=tool_info["env_var"],
                docs_url=tool_info.get("docs_url"),
                is_built_in=False,
            )
        )

    return MCPStatusResponse(
        built_in_tools=built_in,
        configurable_tools=tools,
        scheduler_readiness=_scheduler_readiness(config),
    )


@router.get("/google-workspace-status", response_model=GoogleWorkspaceStatus)
@limiter.limit(get_user_persona_limit)
async def get_google_workspace_status(
    request: Request,
    user_id: str | None = None,
    current_user_id: str = Depends(get_current_user_id),
):
    """Get Google Workspace connection status for a user.

    Checks if the user signed in with Google and has the required tokens
    to access Google Workspace features (Docs, Sheets, Forms, Calendar, Gmail).
    """
    try:
        supabase = get_service_client()

        # Get user's auth provider from Supabase
        user_response = supabase.auth.admin.get_user_by_id(current_user_id)

        if not user_response or not user_response.user:
            return GoogleWorkspaceStatus(connected=False, message="User not found")

        user = user_response.user

        # Check if user signed in with Google
        identities = user.identities or []
        google_identity = None

        for identity in identities:
            if identity.provider == "google":
                google_identity = identity
                break

        if not google_identity:
            return GoogleWorkspaceStatus(
                connected=False,
                provider=None,
                message="Sign in with Google to enable Google Workspace features",
            )

        # User has Google auth - they have access to Workspace features
        email = user.email or google_identity.identity_data.get("email", "")

        # List available features
        features = [
            "Google Docs - Create and edit documents",
            "Google Sheets - Create spreadsheets and track data",
            "Google Forms - Create surveys and feedback forms",
            "Google Calendar - Schedule events and meetings",
            "Gmail - Send emails on your behalf",
        ]

        return GoogleWorkspaceStatus(
            connected=True,
            email=email,
            provider="google",
            features=features,
            message="Google Workspace is connected and ready to use",
        )

    except Exception as e:
        return GoogleWorkspaceStatus(
            connected=False, message=f"Unable to check status: {e!s}"
        )


@router.get("/social-status", response_model=SocialStatusResponse)
@limiter.limit(get_user_persona_limit)
async def get_social_status(
    request: Request,
    user_id: str | None = None,
    current_user_id: str = Depends(get_current_user_id),
):
    """Get status of all social media connections for a user."""
    connector = get_social_connector()
    connections = connector.list_connections(current_user_id)

    # Create a map of platform -> connection
    connection_map = {c["platform"]: c for c in connections}

    platforms = []
    for platform_info in SOCIAL_PLATFORMS_INFO:
        platform_id = platform_info["platform"]
        connection = connection_map.get(platform_id)

        # Check if OAuth credentials are configured
        requires_config = False
        for key in platform_info["config_keys"]:
            if not os.environ.get(key):
                requires_config = True
                break

        platforms.append(
            SocialPlatformStatus(
                platform=platform_id,
                display_name=platform_info["display_name"],
                icon=platform_info["icon"],
                connected=connection is not None
                and connection.get("status") == "active",
                username=connection.get("platform_username") if connection else None,
                connected_at=connection.get("connected_at") if connection else None,
                requires_config=requires_config,
                config_keys=platform_info["config_keys"],
            )
        )

    return SocialStatusResponse(platforms=platforms)


@router.post("/save-user-config", response_model=SaveConfigResponse)
@limiter.limit(get_user_persona_limit)
async def save_user_config(
    request: Request,
    body: SaveConfigRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Save a user-specific configuration value.

    Stores configuration in the user_configurations table.
    Note: This does NOT set environment variables, those must be set
    at the application level.
    """
    # Validate config key against allowlist to prevent arbitrary key writes
    _ALLOWED_CONFIG_KEYS = {
        "notification_preferences", "theme", "language", "timezone",
        "persona", "onboarding_step", "dashboard_layout", "briefing_schedule",
        "email_digest_frequency", "auto_triage_enabled", "sessions",
    }
    if body.key not in _ALLOWED_CONFIG_KEYS:
        return SaveConfigResponse(
            success=False, message=f"Configuration key '{body.key}' is not allowed"
        )

    try:
        client = get_service_client()

        # Upsert user configuration
        client.table("user_configurations").upsert(
            {
                "user_id": current_user_id,
                "config_key": body.key,
                "config_value": body.value,
            },
            on_conflict="user_id,config_key",
        ).execute()

        return SaveConfigResponse(
            success=True, message=f"Configuration '{body.key}' saved successfully"
        )
    except Exception as e:
        return SaveConfigResponse(
            success=False, message=f"Failed to save configuration: {e!s}"
        )


@router.get("/user-configs")
@limiter.limit(get_user_persona_limit)
async def get_user_configs(
    request: Request,
    user_id: str | None = None,
    current_user_id: str = Depends(get_current_user_id),
):
    """Get all user-specific configurations."""
    try:
        client = get_service_client()

        result = (
            client.table("user_configurations")
            .select("config_key, config_value, updated_at")
            .eq("user_id", current_user_id)
            .execute()
        )

        return {"configs": result.data}
    except Exception as e:
        return {"configs": [], "error": str(e)}


@router.get("/session-config", response_model=SessionConfigResponse)
@limiter.limit(get_user_persona_limit)
async def get_session_config(
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
):
    """Get session configuration (user-configurable, falls back to defaults)."""
    defaults = SessionConfigResponse()
    try:
        client = get_service_client()
        result = (
            client.table("user_configurations")
            .select("config_value")
            .eq("user_id", current_user_id)
            .eq("config_key", "sessions")
            .limit(1)
            .execute()
        )
        if result.data:
            import json
            config_data = json.loads(result.data[0]["config_value"])
            return SessionConfigResponse(**{**defaults.model_dump(), **config_data})
    except Exception:
        pass
    return defaults


@router.post("/connect-social", response_model=ConnectSocialResponse)
@limiter.limit(get_user_persona_limit)
async def connect_social(
    request: Request,
    body: ConnectSocialRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Initiate OAuth connection to a social media platform."""
    # Validate redirect_uri against allowed origins to prevent SSRF
    from urllib.parse import urlparse as _urlparse

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    allowed_host = _urlparse(frontend_url).hostname
    redirect_host = _urlparse(body.redirect_uri).hostname
    if redirect_host != allowed_host:
        raise HTTPException(status_code=400, detail="Invalid redirect URI")

    try:
        connector = get_social_connector()
        # Use authenticated user_id, not the body-supplied one (IDOR prevention)
        result = connector.get_authorization_url(
            platform=body.platform, user_id=current_user_id, redirect_uri=body.redirect_uri
        )

        if "error" in result:
            return ConnectSocialResponse(error=result["error"])

        return ConnectSocialResponse(
            authorization_url=result["authorization_url"], state=result["state"]
        )
    except Exception as e:
        return ConnectSocialResponse(error=str(e))


@router.post("/disconnect-social", response_model=SaveConfigResponse)
@limiter.limit(get_user_persona_limit)
async def disconnect_social(
    request: Request,
    body: DisconnectSocialRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Disconnect a social media account."""
    try:
        connector = get_social_connector()
        # Use authenticated user_id, not the body-supplied one (IDOR prevention)
        result = connector.revoke_connection(current_user_id, body.platform)

        return SaveConfigResponse(
            success=result.get("success", False),
            message=result.get("message", "Disconnected successfully"),
        )
    except Exception as e:
        return SaveConfigResponse(success=False, message=f"Failed to disconnect: {e!s}")


@router.get("/oauth/callback/{platform}")
async def oauth_callback(platform: str, code: str, state: str, request: Request):
    """Handle OAuth callback from social media platforms."""
    try:
        connector = get_social_connector()

        # Construct redirect URI (should match what was used in authorization)
        redirect_uri = f"{request.base_url}configuration/oauth/callback/{platform}"

        result = await connector.handle_callback(
            platform=platform, code=code, state=state, redirect_uri=redirect_uri
        )

        if "error" in result:
            return {"success": False, "error": result["error"]}

        return {"success": True, "message": result.get("message")}
    except Exception as e:
        return {"success": False, "error": str(e)}
