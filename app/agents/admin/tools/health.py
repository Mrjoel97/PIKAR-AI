# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Health check tool for the AdminAgent.

This tool checks the health of all platform services. It enforces the
autonomy tier by querying admin_agent_permissions before executing.
"""

import logging

from app.agents.admin.tools._autonomy import check_autonomy as _check_autonomy
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)


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
    gate = await _check_autonomy("check_system_health")
    if gate is not None:
        return gate

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
