# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Cloud Scheduler triggered endpoints.

These endpoints are designed to be triggered by Cloud Scheduler for automated
tasks like daily reports and weekly digests.
"""

import logging
import os
import secrets

from fastapi import APIRouter, Header, HTTPException

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduled", tags=["scheduled"])


def _get_supabase() -> Client:
    """Get Supabase client."""
    return get_service_client()


def _verify_scheduler(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Verify request comes from Cloud Scheduler."""
    expected = (os.environ.get("SCHEDULER_SECRET") or "").strip()
    if not expected:
        logger.error(
            "Scheduler request rejected because SCHEDULER_SECRET is not configured"
        )
        raise HTTPException(status_code=503, detail="Scheduler is not configured")
    if not x_scheduler_secret or not secrets.compare_digest(
        x_scheduler_secret, expected
    ):
        logger.warning("Unauthorized scheduler request")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@router.post("/daily-report")
async def trigger_daily_report(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger daily business report generation."""
    _verify_scheduler(x_scheduler_secret)
    client = _get_supabase()
    job = await execute_async(
        client.table("ai_jobs").insert(
            {
                "job_type": "daily_report",
                "status": "pending",
                "priority": 10,
                "input_data": {"trigger": "scheduled", "type": "daily"},
            }
        ),
        op_name="scheduled.daily_report",
    )
    job_id = job.data[0]["id"] if job.data else None
    logger.info("Daily report job created: %s", job_id)
    return {"status": "queued", "job_id": job_id}


@router.post("/weekly-digest")
async def trigger_weekly_digest(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger weekly digest email generation."""
    _verify_scheduler(x_scheduler_secret)
    client = _get_supabase()
    job = await execute_async(
        client.table("ai_jobs").insert(
            {
                "job_type": "weekly_digest",
                "status": "pending",
                "priority": 10,
                "input_data": {"trigger": "scheduled", "type": "weekly"},
            }
        ),
        op_name="scheduled.weekly_digest",
    )
    job_id = job.data[0]["id"] if job.data else None
    logger.info("Weekly digest job created: %s", job_id)
    return {"status": "queued", "job_id": job_id}


@router.post("/workflow-triggers/tick")
async def trigger_workflow_trigger_tick(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger a scheduler tick for durable workflow triggers."""
    _verify_scheduler(x_scheduler_secret)

    from app.services.workflow_trigger_service import (
        run_workflow_trigger_scheduler_tick,
    )

    results = await run_workflow_trigger_scheduler_tick()
    logger.info(
        "Workflow trigger scheduler tick queued %s trigger job(s)", len(results)
    )
    return {"status": "queued", "count": len(results), "results": results}


@router.post("/triage-tick")
async def trigger_email_triage(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger email triage for all enabled users."""
    _verify_scheduler(x_scheduler_secret)
    from app.services.email_triage_worker import EmailTriageWorker

    client = _get_supabase()
    worker = EmailTriageWorker(supabase_client=client)
    result = await worker.run()
    logger.info("Email triage completed: %s", result)
    return result


@router.post("/briefing-digest")
async def trigger_briefing_digest(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Send daily briefing digest emails to all users with digest enabled.

    Called by Cloud Scheduler (e.g. every hour or at 7 AM UTC).
    Queries ``user_briefing_preferences`` for users with
    ``email_digest_enabled=true`` and ``email_digest_frequency != 'off'``,
    then sends a digest email to each.  Also enriches the email with a
    "Business Snapshot" section from the DailyBriefingAggregator.
    """
    _verify_scheduler(x_scheduler_secret)

    from app.services.briefing_digest_service import send_digest_email
    from app.services.daily_briefing_aggregator import aggregate_daily_briefing

    client = _get_supabase()

    # Fetch users who have digest enabled
    result = await execute_async(
        client.table("user_briefing_preferences")
        .select("user_id")
        .eq("email_digest_enabled", True)
        .neq("email_digest_frequency", "off"),
        op_name="briefing_digest.get_users",
    )

    users = result.data or []
    sent = 0
    errors = 0

    for user_row in users:
        user_id = user_row["user_id"]
        try:
            # Aggregate business briefing data for the email snapshot
            briefing_data = None
            try:
                briefing_data = await aggregate_daily_briefing(user_id)
            except Exception:
                logger.warning(
                    "Could not aggregate briefing data for user %s -- sending digest without snapshot",
                    user_id,
                )

            digest_result = await send_digest_email(
                user_id, briefing_data=briefing_data
            )
            if digest_result.get("sent"):
                sent += 1
        except Exception as exc:
            logger.warning("Failed to send digest to %s: %s", user_id, exc)
            errors += 1

    logger.info(
        "Briefing digest run complete: %d users, %d sent, %d errors",
        len(users),
        sent,
        errors,
    )
    return {"status": "ok", "sent": sent, "errors": errors, "total_users": len(users)}


@router.post("/department-tick")
async def trigger_department_tick(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger autonomous department execution cycles."""
    _verify_scheduler(x_scheduler_secret)

    from app.services.department_runner import runner

    results = await runner.tick()
    logger.info("Department tick completed: %s department(s) processed", len(results))
    return {
        "status": "ok",
        "departments_processed": len(results),
        "results": results,
    }


@router.post("/intelligence-tick")
async def trigger_intelligence_tick(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger scheduled research for all active domains."""
    _verify_scheduler(x_scheduler_secret)

    from app.services.intelligence_scheduler import (
        get_domains_due_for_refresh,
        run_scheduled_research,
    )

    domains = get_domains_due_for_refresh()
    results = []
    for domain_config in domains:
        domain = domain_config["domain"]
        result = await run_scheduled_research(domain)
        results.append(result)

    total_jobs = sum(r.get("jobs_executed", 0) for r in results)
    total_cost = sum(r.get("total_cost", 0) for r in results)

    logger.info(
        "Intelligence tick completed: %d domains, %d jobs, cost=%.4f",
        len(domains),
        total_jobs,
        total_cost,
    )
    return {
        "success": True,
        "domains_processed": len(domains),
        "total_jobs": total_jobs,
        "total_cost": round(total_cost, 4),
        "results": results,
    }


@router.post("/slack-daily-briefing")
async def trigger_slack_daily_briefing(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Send daily briefings to all users with briefing enabled.

    Queries ``notification_channel_config`` for rows where
    ``daily_briefing=True``, aggregates enriched briefing data per user via
    ``DailyBriefingAggregator``, then dispatches to Slack or Teams.
    """
    _verify_scheduler(x_scheduler_secret)

    from datetime import date

    from app.services.daily_briefing_aggregator import (
        aggregate_daily_briefing,
        format_briefing_blocks,
        format_briefing_plain_text,
    )
    from app.services.proactive_alert_service import dispatch_proactive_alert

    client = _get_supabase()
    today_str = date.today().isoformat()

    # Fetch all users with daily briefing enabled
    config_result = await execute_async(
        client.table("notification_channel_config")
        .select("*")
        .eq("daily_briefing", True),
        op_name="slack_daily_briefing.get_configs",
    )
    configs = config_result.data or []

    sent = 0
    errors = 0

    for config_row in configs:
        user_id: str = config_row.get("user_id", "")
        provider: str = config_row.get("provider", "")
        briefing_channel_id: str = config_row.get("briefing_channel_id", "")

        if not user_id or not briefing_channel_id:
            logger.warning(
                "Skipping briefing config with missing user_id or channel: %s",
                config_row.get("id"),
            )
            continue

        try:
            # --- Aggregate enriched briefing data ---
            briefing_data = await aggregate_daily_briefing(user_id)

            # Dispatch to the correct provider
            if provider == "slack":
                from app.services.slack_notification_service import (
                    SlackNotificationService,
                )

                blocks = format_briefing_blocks(briefing_data)
                ok = await SlackNotificationService().send_daily_briefing(
                    user_id, briefing_channel_id, briefing_data, blocks=blocks
                )
            elif provider == "teams":
                from app.services.teams_notification_service import (
                    TeamsNotificationService,
                )

                plain_text = format_briefing_plain_text(briefing_data)
                ok = await TeamsNotificationService().send_daily_briefing(
                    user_id, briefing_channel_id, briefing_data, text=plain_text
                )
            else:
                logger.warning(
                    "Unknown notification provider '%s' for user %s -- skipping",
                    provider,
                    user_id,
                )
                ok = False

            if ok:
                sent += 1
                # Log to proactive_alert_log for dedup (prevents double-send)
                await dispatch_proactive_alert(
                    user_id=user_id,
                    alert_type="daily_briefing",
                    alert_key=today_str,
                    title="Daily Briefing",
                    message=format_briefing_plain_text(briefing_data),
                )
            else:
                errors += 1

        except Exception:
            logger.exception(
                "Failed to send daily briefing to user %s via %s",
                user_id,
                provider,
            )
            errors += 1

    logger.info(
        "Slack daily briefing run complete: %d users, %d sent, %d errors",
        len(configs),
        sent,
        errors,
    )
    return {"status": "ok", "sent": sent, "errors": errors, "total_users": len(configs)}


@router.post("/proactive-briefing")
async def trigger_proactive_briefing(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Send enriched proactive briefings to all users with notification channels configured.

    This is the canonical "morning briefing" endpoint for Cloud Scheduler.
    For each user with any notification channel (Slack/Teams/email), aggregates
    briefing data via ``DailyBriefingAggregator`` and dispatches via
    ``ProactiveAlertService`` (which handles in-app + external channels + dedup).
    """
    _verify_scheduler(x_scheduler_secret)

    from datetime import date

    from app.services.daily_briefing_aggregator import (
        aggregate_daily_briefing,
        format_briefing_plain_text,
    )
    from app.services.proactive_alert_service import dispatch_proactive_alert

    client = _get_supabase()
    today_str = date.today().isoformat()

    # Query all users with any notification channel configured
    config_result = await execute_async(
        client.table("notification_channel_config")
        .select("user_id")
        .eq("daily_briefing", True),
        op_name="proactive_briefing.get_users",
    )

    # Deduplicate user_ids (a user may have multiple channels)
    seen_users: set[str] = set()
    user_ids: list[str] = []
    for row in config_result.data or []:
        uid = row.get("user_id", "")
        if uid and uid not in seen_users:
            seen_users.add(uid)
            user_ids.append(uid)

    sent = 0
    errors = 0

    for user_id in user_ids:
        try:
            briefing_data = await aggregate_daily_briefing(user_id)
            plain_text = format_briefing_plain_text(briefing_data)

            result = await dispatch_proactive_alert(
                user_id=user_id,
                alert_type="daily_briefing",
                alert_key=today_str,
                title="Daily Business Briefing",
                message=plain_text,
                metadata=briefing_data,
            )

            if result.get("dispatched"):
                sent += 1
            else:
                # Likely a dedup skip -- not an error
                logger.debug(
                    "Proactive briefing skipped for user %s: %s",
                    user_id,
                    result.get("reason", "unknown"),
                )
        except Exception:
            logger.exception("Failed to send proactive briefing to user %s", user_id)
            errors += 1

    logger.info(
        "Proactive briefing run complete: %d users, %d sent, %d errors",
        len(user_ids),
        sent,
        errors,
    )
    return {
        "status": "ok",
        "sent": sent,
        "errors": errors,
        "total_users": len(user_ids),
    }


@router.post("/monitoring-tick")
async def trigger_monitoring_tick(
    cadence: str = "daily",
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger monitoring tick for all due user monitoring jobs.

    Args:
        cadence: Scheduler cadence — daily, weekly, or biweekly.
    """
    _verify_scheduler(x_scheduler_secret)
    from app.services.monitoring_job_service import run_monitoring_tick

    results = await run_monitoring_tick(cadence=cadence)
    alerts_dispatched = sum(r.get("proactive_alerts", 0) for r in results)
    logger.info(
        "Monitoring tick completed: cadence=%s, %d job(s) processed, %d alerts dispatched",
        cadence,
        len(results),
        alerts_dispatched,
    )
    return {
        "status": "ok",
        "jobs_run": len(results),
        "alerts_dispatched": alerts_dispatched,
        "results": results,
    }


@router.post("/integration-health-tick")
async def trigger_integration_health_tick(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger integration health check for all users.

    Checks OAuth token expiry (within 3 days) and provider connectivity.
    Dispatches WARNING alerts for expiring tokens and ERROR alerts for
    unhealthy connections via ProactiveAlertService.

    Intended cadence: daily (Cloud Scheduler fires once per day).
    """
    _verify_scheduler(x_scheduler_secret)

    from app.services.integration_health_monitor import run_integration_health_check

    result = await run_integration_health_check()
    logger.info(
        "Integration health tick completed: %d tokens expiring, %d unhealthy, %d alerts sent",
        result.get("tokens_expiring", 0),
        result.get("unhealthy", 0),
        result.get("alerts_sent", 0),
    )
    return {"status": "ok", **result}


@router.post("/anomaly-detection-tick")
async def trigger_anomaly_detection_tick(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger anomaly detection for all active users.

    Queries users who have dashboard_summaries or ad_spend_tracking data
    in the last 7 days, then runs anomaly detection for each.
    """
    _verify_scheduler(x_scheduler_secret)

    from app.services.anomaly_detection_service import run_anomaly_detection_cycle

    client = _get_supabase()

    # Find active users: those with recent dashboard or ad data
    active_user_ids: set[str] = set()

    try:
        from datetime import datetime, timedelta, timezone

        seven_days_ago = (datetime.now(tz=timezone.utc) - timedelta(days=7)).isoformat()
        dashboard_result = await execute_async(
            client.table("dashboard_summaries")
            .select("user_id")
            .gte("created_at", seven_days_ago)
            .limit(1000),
            op_name="anomaly_tick.active_dashboard_users",
        )
        for row in dashboard_result.data or []:
            active_user_ids.add(row["user_id"])
    except Exception:
        logger.warning("Failed to query dashboard_summaries for active users")

    try:
        campaign_result = await execute_async(
            client.table("ad_campaigns").select("user_id").limit(1000),
            op_name="anomaly_tick.active_ad_users",
        )
        for row in campaign_result.data or []:
            active_user_ids.add(row["user_id"])
    except Exception:
        logger.warning("Failed to query ad_campaigns for active users")

    users_checked = 0
    anomalies_found = 0
    alerts_sent = 0

    for user_id in active_user_ids:
        try:
            anomalies = await run_anomaly_detection_cycle(user_id)
            users_checked += 1
            anomalies_found += len(anomalies)
            alerts_sent += sum(1 for a in anomalies if a.get("is_anomaly"))
        except Exception:
            logger.exception("Anomaly detection failed for user=%s", user_id)

    logger.info(
        "Anomaly detection tick complete: %d users, %d anomalies, %d alerts",
        users_checked,
        anomalies_found,
        alerts_sent,
    )
    return {
        "status": "ok",
        "users_checked": users_checked,
        "anomalies_found": anomalies_found,
        "alerts_sent": alerts_sent,
    }


@router.get("/health")
async def scheduler_health():
    """Health check endpoint for Cloud Scheduler."""
    return {"status": "healthy", "service": "pikar-ai-scheduler"}


@router.post("/trigger-job")
async def trigger_custom_job(
    job_type: str,
    priority: int = 5,
    input_data: dict | None = None,
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger a custom ai_job."""
    _verify_scheduler(x_scheduler_secret)
    client = _get_supabase()
    job = await execute_async(
        client.table("ai_jobs").insert(
            {
                "job_type": job_type,
                "status": "pending",
                "priority": priority,
                "input_data": input_data or {"trigger": "scheduled"},
            }
        ),
        op_name="scheduled.custom_job",
    )
    job_id = job.data[0]["id"] if job.data else None
    logger.info("Custom job created: %s (type: %s)", job_id, job_type)
    return {"status": "queued", "job_id": job_id, "job_type": job_type}
