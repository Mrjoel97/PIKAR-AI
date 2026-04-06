# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""MonitoringJobService — user-defined continuous intelligence monitoring.

Manages monitoring jobs that track competitors, markets, and topics on a
scheduled cadence. Each job runs through the research pipeline, updates the
knowledge graph and vault, and dispatches alert notifications when
significant changes or keyword triggers are detected.

Cadence mapping:
    critical  -> daily
    normal    -> weekly
    low       -> biweekly

Triggered by Cloud Scheduler via POST /scheduled/monitoring-tick.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level lazy wrappers for test patching
# These wrappers are defined at module scope so tests can patch them via
# ``app.services.monitoring_job_service.<name>`` without needing to reach
# into the source modules directly.
# ---------------------------------------------------------------------------


def get_service_client():
    """Lazy-load service-role Supabase client.

    Defined at module level so tests can patch
    ``app.services.monitoring_job_service.get_service_client``.
    """
    from app.services.supabase import get_service_client as _get

    return _get()


def _check_budget(domain: str) -> bool:
    """Lazy wrapper around adaptive_router._check_budget for test patching."""
    from app.agents.research.tools.adaptive_router import _check_budget as _cb

    return _cb(domain)


async def _execute_research_job(
    query: str, domain: str, depth: str, triggered_by: str = "scheduled"
) -> dict[str, Any]:
    """Lazy wrapper around intelligence_scheduler._execute_research_job."""
    from app.services.intelligence_scheduler import (
        _execute_research_job as _erj,
    )

    return await _erj(
        query=query, domain=domain, depth=depth, triggered_by=triggered_by
    )


async def dispatch_notification(
    user_id: str, event_type: str, payload: dict[str, Any]
) -> dict[str, bool]:
    """Lazy wrapper around notification_dispatcher.dispatch_notification."""
    from app.services.notification_dispatcher import (
        dispatch_notification as _dn,
    )

    return await _dn(user_id=user_id, event_type=event_type, payload=payload)


def write_to_graph(synthesis: dict, domain: str = "general") -> dict[str, Any]:
    """Lazy wrapper around graph_writer.write_to_graph."""
    from app.agents.research.tools.graph_writer import write_to_graph as _wtg

    return _wtg(synthesis, domain=domain)


async def write_to_vault(
    synthesis: dict, topic: str = "", domain: str = "general"
) -> dict[str, Any]:
    """Lazy wrapper around graph_writer.write_to_vault."""
    from app.agents.research.tools.graph_writer import write_to_vault as _wtv

    return await _wtv(synthesis, topic=topic)


# ---------------------------------------------------------------------------
# AI significance check (module-level for easy test patching)
# ---------------------------------------------------------------------------


async def _is_significant_change(old_text: str, new_text: str, topic: str) -> bool:
    """Use Gemini to determine if findings represent a significant change.

    Returns False on any error so callers degrade gracefully.

    Args:
        old_text: Previous state context (hash or summary).
        new_text: Current findings text.
        topic: Monitoring topic for context.

    Returns:
        True if the change is significant.
    """
    try:
        import google.generativeai as genai  # type: ignore[import-untyped]

        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = (
            f"You are monitoring '{topic}' for significant business changes.\n\n"
            f"New findings summary:\n{new_text[:1000]}\n\n"
            "Is this a significant development worth alerting the user about? "
            "Answer only 'yes' or 'no'."
        )
        response = await model.generate_content_async(prompt)
        answer = (response.text or "").strip().lower()
        return answer.startswith("yes")
    except Exception as exc:
        logger.warning("Significance check failed for '%s': %s", topic, exc)
        return False


# ---------------------------------------------------------------------------
# MonitoringJobService
# ---------------------------------------------------------------------------


class MonitoringJobService:
    """CRUD and execution service for user-defined monitoring jobs.

    Uses service role (get_service_client) so background tick operations
    bypass RLS — matching the AdminService pattern used in other background
    services like EmailSequenceService and AdBudgetCapService.

    All supabase calls use direct synchronous .execute() (matching
    intelligence_scheduler.py and graph_writer.py patterns) rather than
    execute_async, because monitoring tick runs are orchestrated by the
    async run_monitoring_tick method which handles awaiting at the
    application level.
    """

    def __init__(self) -> None:
        """Initialise with service-role Supabase client."""
        self._client = get_service_client()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_job(
        self,
        user_id: str,
        topic: str,
        monitoring_type: str = "competitor",
        importance: str = "normal",
        keyword_triggers: list[str] | None = None,
        pinned_urls: list[str] | None = None,
        excluded_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        """Insert a new monitoring job and return the created row.

        Args:
            user_id: Supabase auth user ID.
            topic: Topic, company, or market to monitor.
            monitoring_type: One of "competitor", "market", "topic".
            importance: One of "critical" (daily), "normal" (weekly), "low" (biweekly).
            keyword_triggers: Alert keywords (case-insensitive matching).
            pinned_urls: URLs to always include in research.
            excluded_urls: URLs to exclude from research.

        Returns:
            Created monitoring job dict.
        """
        row = {
            "user_id": user_id,
            "topic": topic,
            "monitoring_type": monitoring_type,
            "importance": importance,
            "keyword_triggers": keyword_triggers or [],
            "pinned_urls": pinned_urls or [],
            "excluded_urls": excluded_urls or [],
            "is_active": True,
        }
        result = self._client.table("monitoring_jobs").insert(row).execute()
        return result.data[0] if result.data else row

    async def list_jobs(self, user_id: str) -> list[dict[str, Any]]:
        """Return all monitoring jobs for the given user, newest first.

        Args:
            user_id: Supabase auth user ID.

        Returns:
            List of monitoring job dicts.
        """
        result = (
            self._client.table("monitoring_jobs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    async def update_job(
        self, job_id: str, user_id: str, **updates: Any
    ) -> dict[str, Any]:
        """Update allowed fields on a monitoring job.

        Only is_active, importance, keyword_triggers, pinned_urls, excluded_urls
        may be changed. unknown fields are silently ignored.

        Args:
            job_id: Job UUID.
            user_id: Owner's user ID (ownership check via .eq).
            **updates: Fields to update.

        Returns:
            Updated monitoring job dict.
        """
        _allowed = {
            "is_active",
            "importance",
            "keyword_triggers",
            "pinned_urls",
            "excluded_urls",
        }
        safe_updates = {k: v for k, v in updates.items() if k in _allowed}
        safe_updates["updated_at"] = datetime.now(tz=timezone.utc).isoformat()

        result = (
            self._client.table("monitoring_jobs")
            .update(safe_updates)
            .eq("id", job_id)
            .eq("user_id", user_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    async def delete_job(self, job_id: str, user_id: str) -> dict[str, Any]:
        """Delete a monitoring job owned by user_id.

        Args:
            job_id: Job UUID.
            user_id: Owner's user ID (ownership check via .eq).

        Returns:
            Dict with deleted=True and job_id.
        """
        self._client.table("monitoring_jobs").delete().eq("id", job_id).eq(
            "user_id", user_id
        ).execute()
        return {"deleted": True, "job_id": job_id}

    # ------------------------------------------------------------------
    # Scheduling helpers
    # ------------------------------------------------------------------

    async def get_due_jobs(self, cadence: str) -> list[dict[str, Any]]:
        """Return active jobs that are due based on the cadence.

        Importance-to-cadence mapping:
            daily    -> critical only
            weekly   -> critical + normal
            biweekly -> all active jobs

        Args:
            cadence: One of "daily", "weekly", "biweekly".

        Returns:
            List of due monitoring job dicts.
        """
        query = self._client.table("monitoring_jobs").select("*").eq("is_active", True)

        if cadence == "daily":
            query = query.eq("importance", "critical")
        elif cadence == "weekly":
            query = query.in_("importance", ["critical", "normal"])
        # biweekly: all active jobs — no additional importance filter

        result = query.execute()
        return result.data or []

    # ------------------------------------------------------------------
    # Monitoring tick
    # ------------------------------------------------------------------

    async def run_monitoring_tick(
        self, cadence: str = "daily"
    ) -> list[dict[str, Any]]:
        """Execute the monitoring tick for all jobs due at this cadence.

        For each due job:
        1. Check research budget — skip if exhausted.
        2. Execute research pipeline via _execute_research_job.
        3. Compute SHA256 hash of synthesis findings text.
        4. Compare with previous_state_hash:
           - If changed: keyword match always alerts; otherwise AI significance check.
        5. Write findings to knowledge graph and vault.
        6. Update last_run_at and previous_state_hash.

        Args:
            cadence: One of "daily", "weekly", "biweekly".

        Returns:
            List of dicts: {job_id, status, alerted}.
        """
        jobs = await self.get_due_jobs(cadence)
        results: list[dict[str, Any]] = []

        for job in jobs:
            job_id: str = job["id"]
            user_id: str = job["user_id"]
            topic: str = job["topic"]
            importance: str = job.get("importance", "normal")
            keyword_triggers: list[str] = job.get("keyword_triggers") or []
            previous_hash: str | None = job.get("previous_state_hash")

            # 1. Budget check before executing research
            if not _check_budget("research"):
                logger.info(
                    "Budget exhausted — skipping monitoring job %s (%s)", job_id, topic
                )
                results.append({"job_id": job_id, "status": "skipped", "alerted": False})
                continue

            # 2. Execute research pipeline
            depth = "deep" if importance == "critical" else "standard"
            try:
                research_result = await _execute_research_job(
                    query=topic,
                    domain="research",
                    depth=depth,
                    triggered_by="monitoring",
                )
            except Exception as exc:
                logger.error("Research job error for job %s ('%s'): %s", job_id, topic, exc)
                results.append({"job_id": job_id, "status": "error", "alerted": False})
                continue

            if not research_result.get("success"):
                logger.warning(
                    "Research returned failure for job %s: %s",
                    job_id,
                    research_result.get("error"),
                )
                results.append({"job_id": job_id, "status": "error", "alerted": False})
                continue

            # Extract synthesis from result (supports both flat and nested shapes)
            synthesis: dict[str, Any] = research_result.get("synthesis") or {}
            findings_list = synthesis.get("findings", [])
            findings_text = " ".join(f.get("text", "") for f in findings_list)

            # 3. Compute hash of findings text
            new_hash = hashlib.sha256(findings_text.encode()).hexdigest()
            alerted = False

            # 4. Decide whether to alert
            hash_changed = (previous_hash is None) or (new_hash != previous_hash)

            if hash_changed:
                # Keyword match always alerts regardless of AI judgment
                keyword_matched = bool(
                    keyword_triggers
                    and any(kw.lower() in findings_text.lower() for kw in keyword_triggers)
                )

                if keyword_matched:
                    should_alert = True
                elif previous_hash is not None:
                    # AI significance check only if there's a previous state to compare
                    should_alert = await _is_significant_change(
                        old_text=previous_hash,
                        new_text=findings_text,
                        topic=topic,
                    )
                else:
                    # First run with no previous hash — do not alert on initial run
                    should_alert = False

                if should_alert:
                    summary = findings_text[:300] if findings_text else f"New intelligence available for {topic}"
                    try:
                        await dispatch_notification(
                            user_id=user_id,
                            event_type="monitoring.alert",
                            payload={
                                "title": f"Intelligence Alert: {topic}",
                                "body": summary,
                                "job_id": job_id,
                                "monitoring_type": job.get("monitoring_type", "competitor"),
                            },
                        )
                        alerted = True
                    except Exception as exc:
                        logger.warning(
                            "Notification dispatch failed for job %s: %s", job_id, exc
                        )

            # 5. Write to knowledge graph and vault
            vault_result: dict[str, Any] = {}
            try:
                write_to_graph(synthesis, domain="research")
                vault_result = await write_to_vault(synthesis, topic=topic)
            except Exception as exc:
                logger.warning("Graph/vault write failed for job %s: %s", job_id, exc)

            # 6. Update job state
            update_payload: dict[str, Any] = {
                "last_run_at": datetime.now(tz=timezone.utc).isoformat(),
                "previous_state_hash": new_hash,
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            }
            # Store vault doc reference if available
            embedding_ids = vault_result.get("embedding_ids", []) if vault_result else []
            if embedding_ids:
                update_payload["last_brief_id"] = embedding_ids[0]

            try:
                self._client.table("monitoring_jobs").update(update_payload).eq(
                    "id", job_id
                ).execute()
            except Exception as exc:
                logger.warning("Job state update failed for %s: %s", job_id, exc)

            results.append({"job_id": job_id, "status": "success", "alerted": alerted})

        return results


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


async def run_monitoring_tick(cadence: str = "daily") -> list[dict[str, Any]]:
    """Instantiate MonitoringJobService and execute the monitoring tick.

    This is the entry point called by the /scheduled/monitoring-tick endpoint.

    Args:
        cadence: One of "daily", "weekly", "biweekly".

    Returns:
        List of {job_id, status, alerted} dicts.
    """
    svc = MonitoringJobService()
    return await svc.run_monitoring_tick(cadence=cadence)
