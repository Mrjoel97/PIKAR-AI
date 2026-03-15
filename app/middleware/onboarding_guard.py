"""Middleware to guard dashboard routes for users who haven't completed onboarding."""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Paths that don't require onboarding completion
EXCLUDED_PREFIXES = (
    "/auth",
    "/onboarding",
    "/health",
    "/a2a",
    "/docs",
    "/openapi",
    "/static",
    "/favicon",
    "/_next",
)


class OnboardingGuardMiddleware(BaseHTTPMiddleware):
    """Redirect unauthenticated or non-onboarded users away from protected routes.

    Checks the onboarding_completed flag for authenticated users.
    Returns 302 redirect to /onboarding for users who haven't completed onboarding.
    Excluded paths (auth, onboarding, health, etc.) are always allowed through.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip excluded paths
        if any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            return await call_next(request)

        # Only check for paths that look like they need protection
        # (dashboard, persona routes, briefing, etc.)
        protected_prefixes = ("/dashboard", "/solopreneur", "/startup", "/sme", "/enterprise", "/briefing", "/settings")
        if not any(path.startswith(prefix) for prefix in protected_prefixes):
            return await call_next(request)

        # Try to extract user from auth header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            # No auth token — let the route's own auth handle it
            return await call_next(request)

        token = auth_header.split(" ", 1)[1]

        try:
            from app.services.supabase import get_service_client
            supabase = get_service_client()
            user = supabase.auth.get_user(token)
            if not user or not user.user:
                return await call_next(request)

            user_id = user.user.id

            # Check onboarding status — check users_profile first, fallback to user_executive_agents
            profile = supabase.table("users_profile").select("persona").eq("user_id", user_id).maybe_single().execute()
            if profile.data and profile.data.get("persona"):
                # Has persona = onboarding completed
                return await call_next(request)

            # Check legacy table
            agent_config = supabase.table("user_executive_agents").select("onboarding_completed").eq("user_id", user_id).maybe_single().execute()
            if agent_config.data and agent_config.data.get("onboarding_completed"):
                return await call_next(request)

            # User hasn't completed onboarding
            logger.info(f"User {user_id} redirected to onboarding (not completed)")
            return JSONResponse(
                status_code=302,
                headers={"Location": "/onboarding"},
                content={"detail": "Onboarding not completed", "redirect": "/onboarding"}
            )

        except Exception as e:
            logger.warning(f"Onboarding guard check failed: {e}")
            # Don't block on guard failures — let the request through
            return await call_next(request)
