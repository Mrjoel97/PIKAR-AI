# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Monitoring agent tools for continuous intelligence job management.

Exposes MONITORING_TOOLS for the ResearchAgent so users can create, list,
pause, resume, and delete monitoring jobs via natural language chat.

Following the raw-function-export pattern (matching ad_platform_tools.py):
- All functions are plain Python (not FunctionTool) — sanitize_tools wraps them.
- user_id extracted from request-scoped context via _get_user_id().
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Schedule descriptions shown to users
_SCHEDULE_TEXT: dict[str, str] = {
    "critical": "daily",
    "normal": "weekly",
    "low": "biweekly",
}

_VALID_MONITORING_TYPES = {"competitor", "market", "topic"}
_VALID_IMPORTANCE = {"critical", "normal", "low"}


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


async def create_monitoring_job(
    topic: str,
    monitoring_type: str = "competitor",
    importance: str = "normal",
    keyword_triggers: list[str] | None = None,
    pinned_urls: list[str] | None = None,
    excluded_urls: list[str] | None = None,
) -> dict[str, Any]:
    """Create a continuous intelligence monitoring job.

    Creates a scheduled monitoring job that tracks a competitor, market, or
    topic and alerts you when significant changes are detected.

    Args:
        topic: What to monitor (e.g. "Acme Corp pricing strategy", "SaaS market trends").
        monitoring_type: One of: competitor, market, topic.
        importance: Schedule cadence — critical (daily), normal (weekly), low (biweekly).
        keyword_triggers: Words that always trigger an alert when found in findings.
        pinned_urls: Specific URLs to always include in research.
        excluded_urls: URLs to skip during research.

    Returns:
        Dict with status, job details, schedule description, and confirmation message.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    if monitoring_type not in _VALID_MONITORING_TYPES:
        return {
            "error": f"Invalid monitoring_type '{monitoring_type}'. Must be one of: {', '.join(sorted(_VALID_MONITORING_TYPES))}"
        }
    if importance not in _VALID_IMPORTANCE:
        return {
            "error": f"Invalid importance '{importance}'. Must be one of: {', '.join(sorted(_VALID_IMPORTANCE))}"
        }

    try:
        from app.services.monitoring_job_service import MonitoringJobService

        service = MonitoringJobService()
        job = await service.create_job(
            user_id=user_id,
            topic=topic,
            monitoring_type=monitoring_type,
            importance=importance,
            keyword_triggers=keyword_triggers,
            pinned_urls=pinned_urls,
            excluded_urls=excluded_urls,
        )
        schedule = _SCHEDULE_TEXT.get(importance, "weekly")
        return {
            "status": "success",
            "job": job,
            "schedule": f"Runs {schedule} based on {importance} importance",
            "message": (
                f"Now monitoring '{topic}'. You'll receive alerts when significant "
                f"changes are detected. First run scheduled {schedule}."
            ),
        }
    except Exception as exc:
        logger.error("create_monitoring_job failed: %s", exc)
        return {"error": f"Failed to create monitoring job: {exc}"}


async def list_monitoring_jobs() -> dict[str, Any]:
    """List all active monitoring jobs.

    Returns a summary of your current monitoring jobs with their topics,
    types, importance levels, and schedule descriptions.

    Returns:
        Dict with status, jobs list (with schedule descriptions), and count.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.monitoring_job_service import MonitoringJobService

        service = MonitoringJobService()
        raw_jobs = await service.list_jobs(user_id=user_id)

        # Enrich with schedule description
        jobs = []
        for job in raw_jobs:
            imp = job.get("importance", "normal")
            jobs.append(
                {
                    **job,
                    "schedule_description": _SCHEDULE_TEXT.get(imp, "weekly"),
                }
            )

        return {"status": "success", "jobs": jobs, "count": len(jobs)}
    except Exception as exc:
        logger.error("list_monitoring_jobs failed: %s", exc)
        return {"error": f"Failed to list monitoring jobs: {exc}"}


async def pause_monitoring_job(job_id: str) -> dict[str, Any]:
    """Pause a monitoring job (stop scheduled runs without deleting it).

    Args:
        job_id: UUID of the monitoring job to pause.

    Returns:
        Dict with status and confirmation message.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.monitoring_job_service import MonitoringJobService

        service = MonitoringJobService()
        job = await service.update_job(job_id=job_id, user_id=user_id, is_active=False)
        if not job:
            return {"error": f"Monitoring job {job_id} not found"}
        return {
            "status": "success",
            "job": job,
            "message": f"Monitoring job '{job.get('topic', job_id)}' paused. Resume it any time.",
        }
    except Exception as exc:
        logger.error("pause_monitoring_job failed: %s", exc)
        return {"error": f"Failed to pause monitoring job: {exc}"}


async def resume_monitoring_job(job_id: str) -> dict[str, Any]:
    """Resume a paused monitoring job.

    Args:
        job_id: UUID of the monitoring job to resume.

    Returns:
        Dict with status and confirmation message.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.monitoring_job_service import MonitoringJobService

        service = MonitoringJobService()
        job = await service.update_job(job_id=job_id, user_id=user_id, is_active=True)
        if not job:
            return {"error": f"Monitoring job {job_id} not found"}
        imp = job.get("importance", "normal")
        schedule = _SCHEDULE_TEXT.get(imp, "weekly")
        return {
            "status": "success",
            "job": job,
            "message": (
                f"Monitoring job '{job.get('topic', job_id)}' resumed. "
                f"Next run will be {schedule}."
            ),
        }
    except Exception as exc:
        logger.error("resume_monitoring_job failed: %s", exc)
        return {"error": f"Failed to resume monitoring job: {exc}"}


async def delete_monitoring_job(job_id: str) -> dict[str, Any]:
    """Permanently delete a monitoring job.

    Args:
        job_id: UUID of the monitoring job to delete.

    Returns:
        Dict with status and confirmation message.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.monitoring_job_service import MonitoringJobService

        service = MonitoringJobService()
        result = await service.delete_job(job_id=job_id, user_id=user_id)
        return {
            "status": "success",
            "deleted_id": result.get("id", job_id),
            "message": f"Monitoring job {job_id} permanently deleted.",
        }
    except Exception as exc:
        logger.error("delete_monitoring_job failed: %s", exc)
        return {"error": f"Failed to delete monitoring job: {exc}"}


# Exported tool list for ResearchAgent
MONITORING_TOOLS = [
    create_monitoring_job,
    list_monitoring_jobs,
    pause_monitoring_job,
    resume_monitoring_job,
    delete_monitoring_job,
]
