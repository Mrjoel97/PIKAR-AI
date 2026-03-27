# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Middleware to guard dashboard routes for users who haven't completed onboarding."""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.supabase import get_service_client

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

# Paths that require onboarding completion
PROTECTED_PREFIXES = (
    "/dashboard",
    "/solopreneur",
    "/startup",
    "/sme",
    "/enterprise",
    "/briefing",
    "/settings",
)


class OnboardingGuardMiddleware(BaseHTTPMiddleware):
    """Guard protected routes for users who haven't completed onboarding.

    Checks the onboarding_completed flag for authenticated users on protected paths.
    Returns a redirect to /onboarding for users who haven't completed onboarding.
    Excluded paths (auth, onboarding, health, etc.) are always allowed through.
    """

    async def dispatch(self, request, call_next):
        """Check onboarding status and redirect if needed."""
        path = request.url.path

        # Skip excluded paths
        if any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            return await call_next(request)

        # Only check protected paths
        if not any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES):
            return await call_next(request)

        # Try to extract user from auth header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            # No auth token — let the route's own auth handle it
            return await call_next(request)

        token = auth_header.split(" ", 1)[1]

        try:
            supabase = get_service_client()
            user = supabase.auth.get_user(token)
            if not user or not user.user:
                return await call_next(request)

            user_id = user.user.id

            # Check onboarding status — users_profile first, fallback to legacy
            profile = (
                supabase.table("users_profile")
                .select("persona")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if profile.data and profile.data.get("persona"):
                return await call_next(request)

            # Check legacy table
            agent_config = (
                supabase.table("user_executive_agents")
                .select("onboarding_completed")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if agent_config.data and agent_config.data.get("onboarding_completed"):
                return await call_next(request)

            # User hasn't completed onboarding — return JSON for API clients
            # (frontend Next.js middleware handles browser redirects)
            logger.info("User %s redirected to onboarding (not completed)", user_id)
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Onboarding not completed",
                    "redirect": "/onboarding",
                },
            )

        except Exception as e:
            logger.warning("Onboarding guard check failed: %s", e)
            # Don't block on guard failures — let the request through
            return await call_next(request)
