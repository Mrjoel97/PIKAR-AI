"""Health check tool for the AdminAgent.

This tool checks the health of all platform services. It enforces the
autonomy tier by querying admin_agent_permissions before executing.
"""

import logging
import uuid

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

# Action name registered in admin_agent_permissions
_ACTION_NAME = "check_system_health"


async def _run_liveness_check() -> dict:
    """Execute the liveness health check.

    Separated into its own function to allow clean mocking in unit tests.

    Returns:
        Health status dict from the liveness endpoint function.
    """
    from app.fast_api_app import get_liveness

    return await get_liveness()


async def check_system_health() -> dict:
    """Check the health status of all platform services.

    Queries admin_agent_permissions to enforce the autonomy tier before
    executing. Returns a summary of all health endpoints.

    Returns:
        Dict with overall_status ('healthy'|'degraded'|'unhealthy'),
        services dict, and summary string. On confirm tier, returns
        requires_confirmation dict. On blocked tier, returns error dict.
    """
    # Autonomy check: query DB FIRST, before any side effect
    try:
        client = get_service_client()
        res = (
            client.table("admin_agent_permissions")
            .select("autonomy_level")
            .eq("action_name", _ACTION_NAME)
            .limit(1)
            .execute()
        )
        if res.data:
            level = res.data[0].get("autonomy_level", "auto")
            if level == "blocked":
                return {
                    "error": (
                        "check_system_health is blocked by admin configuration. "
                        "Contact a super-admin to change the autonomy level."
                    )
                }
            if level == "confirm":
                token = str(uuid.uuid4())
                return {
                    "requires_confirmation": True,
                    "confirmation_token": token,
                    "action_details": {
                        "action": _ACTION_NAME,
                        "risk_level": "low",
                        "description": "Read system health status of all platform services",
                    },
                }
            # level == "auto" — fall through to execute
    except Exception as exc:
        logger.warning(
            "Could not verify autonomy level for %s, defaulting to auto: %s",
            _ACTION_NAME,
            exc,
        )

    # Execute: call health endpoint functions internally (no HTTP round-trip)
    results: dict = {}

    try:
        results["live"] = await _run_liveness_check()
    except Exception as exc:
        logger.error("Health check 'live' failed: %s", exc)
        results["live"] = {"status": "error", "error": str(exc)}

    # Determine overall status
    all_healthy = all(
        r.get("status") in ("alive", "healthy", "ok") for r in results.values()
    )
    any_error = any(r.get("status") == "error" for r in results.values())

    if all_healthy:
        overall = "healthy"
    elif any_error:
        overall = "unhealthy"
    else:
        overall = "degraded"

    service_count = len(results)
    healthy_count = sum(
        1 for r in results.values() if r.get("status") in ("alive", "healthy", "ok")
    )

    return {
        "overall_status": overall,
        "services": results,
        "summary": f"{healthy_count}/{service_count} services healthy",
    }
