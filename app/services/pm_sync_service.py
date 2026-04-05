# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""PMSyncService -- Bidirectional PM tool sync orchestrator.

Provides:
- Status mapping seeding and CRUD (external state → Pikar status)
- Bidirectional sync: external PM tasks → synced_tasks (with Redis skip-flag)
- Pikar → external PM push (update issue/task on Linear or Asana)
- Initial bulk sync for newly configured projects
- Sync config persistence (project_ids stored in integration_sync_state)

Loop prevention uses short-lived Redis flags
(``pikar:pm:skip:{provider}:{external_id}``, TTL 30s) so that an inbound
webhook that triggers an outbound update does not echo back as another
inbound event.

Conflict resolution: last-write-wins — the most recently updated record
takes precedence.  Conflicts are logged but not blocked.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

from app.services.base_service import AdminService, BaseService
from app.services.integration_manager import IntegrationManager
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class PMSyncService(BaseService):
    """Bidirectional sync orchestrator for Linear and Asana.

    Status mapping is stored in ``pm_status_mappings`` and keyed by
    ``(user_id, provider, external_state_id)``.  Default mappings are
    seeded on first sync config save so every workflow state has a
    reasonable Pikar equivalent even before the user customises them.

    Args:
        user_token: User JWT for Supabase RLS (passed to BaseService).
    """

    #: Default mapping of Linear state.type values to Pikar statuses.
    LINEAR_DEFAULT_MAPPINGS: ClassVar[dict[str, str]] = {
        "triage": "pending",
        "backlog": "pending",
        "unstarted": "pending",
        "started": "in_progress",
        "completed": "completed",
        "cancelled": "cancelled",
    }

    #: Default mapping of Asana section name keywords to Pikar statuses.
    ASANA_DEFAULT_MAPPINGS: ClassVar[dict[str, str]] = {
        "to do": "pending",
        "todo": "pending",
        "backlog": "pending",
        "not started": "pending",
        "in progress": "in_progress",
        "doing": "in_progress",
        "active": "in_progress",
        "done": "completed",
        "complete": "completed",
        "completed": "completed",
        "finished": "completed",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "blocked": "pending",
    }

    # ------------------------------------------------------------------
    # Redis skip-flag helpers
    # ------------------------------------------------------------------

    async def _set_skip_flag(
        self, provider: str, external_id: str, ttl: int = 30
    ) -> None:
        """Set a short-lived Redis flag to suppress sync echo.

        Args:
            provider: Provider key (``"linear"`` or ``"asana"``).
            external_id: External task/issue ID.
            ttl: Time-to-live in seconds (default 30).
        """
        try:
            from app.services.cache import get_cache_service

            cache = get_cache_service()
            redis_client = await cache._get_redis()
            if redis_client is not None:
                key = f"pikar:pm:skip:{provider}:{external_id}"
                await redis_client.setex(key, ttl, "1")
        except Exception:
            logger.warning(
                "Failed to set PM skip flag for %s:%s", provider, external_id
            )

    async def _check_skip_flag(self, provider: str, external_id: str) -> bool:
        """Check whether the skip flag is set (our own echo).

        Args:
            provider: Provider key.
            external_id: External task/issue ID.

        Returns:
            ``True`` if the flag is set (should skip processing).
        """
        try:
            from app.services.cache import get_cache_service

            cache = get_cache_service()
            redis_client = await cache._get_redis()
            if redis_client is not None:
                key = f"pikar:pm:skip:{provider}:{external_id}"
                val = await redis_client.get(key)
                return val is not None
        except Exception:
            logger.warning(
                "Failed to check PM skip flag for %s:%s",
                provider,
                external_id,
            )
        return False

    # ------------------------------------------------------------------
    # Status mapping
    # ------------------------------------------------------------------

    async def seed_status_mappings(
        self,
        user_id: str,
        provider: str,
        states: list[dict[str, Any]],
    ) -> None:
        """Seed default status mappings for all workflow states/sections.

        Inserts a default mapping for each state only if one does not
        already exist (uses ``on_conflict`` ignore pattern).

        For Linear, the state ``type`` field is used to look up the
        default Pikar status.  For Asana, the section name is matched
        against keyword patterns.

        Args:
            user_id: The owning user's UUID.
            provider: Provider key (``"linear"`` or ``"asana"``).
            states: List of state/section dicts from the provider.
                Linear: ``{id, name, type, ...}``
                Asana: ``{gid, name, ...}``
        """
        admin = AdminService()
        rows: list[dict[str, Any]] = []

        for state in states:
            if provider == "linear":
                external_state_id = state.get("id", "")
                external_state_name = state.get("name", "")
                state_type = (state.get("type") or "").lower()
                pikar_status = self.LINEAR_DEFAULT_MAPPINGS.get(state_type, "pending")
            else:  # asana
                external_state_id = state.get("gid", "")
                external_state_name = state.get("name", "")
                name_lower = external_state_name.lower()
                pikar_status = "pending"  # default
                for keyword, status in self.ASANA_DEFAULT_MAPPINGS.items():
                    if keyword in name_lower:
                        pikar_status = status
                        break

            if not external_state_id:
                continue

            rows.append(
                {
                    "user_id": user_id,
                    "provider": provider,
                    "external_state_id": external_state_id,
                    "external_state_name": external_state_name,
                    "pikar_status": pikar_status,
                }
            )

        if rows:
            await execute_async(
                admin.client.table("pm_status_mappings").upsert(
                    rows,
                    on_conflict="user_id,provider,external_state_id",
                    ignore_duplicates=True,
                ),
                op_name="pm_sync.seed_status_mappings",
            )
            logger.info(
                "Seeded %d status mappings for user=%s provider=%s",
                len(rows),
                user_id,
                provider,
            )

    async def get_status_mapping(self, user_id: str, provider: str) -> dict[str, str]:
        """Return the full status mapping for a user + provider.

        Args:
            user_id: The owning user's UUID.
            provider: Provider key.

        Returns:
            Dict of ``external_state_id`` → ``pikar_status``.
        """
        admin = AdminService()
        result = await execute_async(
            admin.client.table("pm_status_mappings")
            .select("external_state_id,pikar_status")
            .eq("user_id", user_id)
            .eq("provider", provider),
            op_name="pm_sync.get_status_mapping",
        )
        return {
            row["external_state_id"]: row["pikar_status"] for row in (result.data or [])
        }

    async def map_external_to_pikar(
        self, user_id: str, provider: str, external_state_id: str
    ) -> str:
        """Map an external workflow state ID to a Pikar status.

        Args:
            user_id: The owning user's UUID.
            provider: Provider key.
            external_state_id: External state/section ID.

        Returns:
            Pikar status string; defaults to ``"pending"`` if unmapped.
        """
        mapping = await self.get_status_mapping(user_id, provider)
        return mapping.get(external_state_id, "pending")

    async def map_pikar_to_external(
        self, user_id: str, provider: str, pikar_status: str
    ) -> str | None:
        """Reverse-map a Pikar status to an external state ID.

        Returns the first external_state_id that maps to the given
        pikar_status.  Used when pushing status changes from Pikar to
        the external PM tool.

        Args:
            user_id: The owning user's UUID.
            provider: Provider key.
            pikar_status: Pikar status (``"pending"``, ``"in_progress"``,
                ``"completed"``, or ``"cancelled"``).

        Returns:
            First matching external state ID, or ``None`` if no mapping
            exists for this status.
        """
        mapping = await self.get_status_mapping(user_id, provider)
        for ext_id, p_status in mapping.items():
            if p_status == pikar_status:
                return ext_id
        return None

    # ------------------------------------------------------------------
    # Bidirectional sync: external → Pikar
    # ------------------------------------------------------------------

    async def sync_from_external(
        self,
        user_id: str,
        provider: str,
        external_issue: dict[str, Any],
    ) -> dict[str, Any]:
        """Sync a single external issue/task into ``synced_tasks``.

        Checks the Redis skip flag to avoid processing our own echo.
        Maps the external status to a Pikar status via status mappings.
        Upserts the record using last-write-wins (no blocking on conflict).
        Sets the skip flag after writing to prevent the DB write from
        triggering a re-echo if webhooks are configured.

        Args:
            user_id: The owning user's UUID.
            provider: Provider key (``"linear"`` or ``"asana"``).
            external_issue: Raw issue/task dict from the provider API.
                Linear: keys include ``id``, ``title``, ``description``,
                    ``state``, ``priority``, ``assignee``, ``labels``,
                    ``url``, ``updatedAt``.
                Asana: keys include ``gid``, ``name``, ``notes``,
                    ``memberships``, ``assignee``, ``permalink_url``.

        Returns:
            The upserted ``synced_tasks`` row.
        """
        admin = AdminService()

        # Resolve external ID
        if provider == "linear":
            external_id = external_issue.get("id", "")
        else:
            external_id = external_issue.get("gid", "")

        if not external_id:
            raise ValueError("External issue has no ID")

        # Check skip flag — if set, this is our own echo; skip it
        if await self._check_skip_flag(provider, external_id):
            logger.info(
                "Skipping PM sync echo: provider=%s external_id=%s",
                provider,
                external_id,
            )
            # Return existing record
            result = await execute_async(
                admin.client.table("synced_tasks")
                .select("*")
                .eq("user_id", user_id)
                .eq("provider", provider)
                .eq("external_id", external_id)
                .limit(1),
                op_name="pm_sync.sync_from_external.skip_read",
            )
            return result.data[0] if result.data else {}

        # Resolve status
        if provider == "linear":
            state = external_issue.get("state") or {}
            external_state_id = state.get("id", "")
        else:
            # Asana: derive state from first membership section
            memberships = external_issue.get("memberships") or []
            section = memberships[0].get("section", {}) if memberships else {}
            external_state_id = section.get("gid", "")

        pikar_status = await self.map_external_to_pikar(
            user_id, provider, external_state_id
        )

        # Build synced_tasks row
        if provider == "linear":
            title = external_issue.get("title", "")
            description = external_issue.get("description") or ""
            assignee_obj = external_issue.get("assignee")
            assignee = assignee_obj.get("name", "") if assignee_obj else ""
            labels_obj = external_issue.get("labels") or {}
            label_nodes = labels_obj.get("nodes") or []
            labels = [ln.get("name", "") for ln in label_nodes if ln.get("name")]
            external_url = external_issue.get("url") or ""
            external_project_id = ""  # resolved at higher level if needed

            # Map Linear priority integer to Pikar priority string
            prio_int = external_issue.get("priority", 0) or 0
            priority_map = {0: "none", 1: "urgent", 2: "high", 3: "medium", 4: "low"}
            priority = priority_map.get(prio_int, "medium")
        else:
            title = external_issue.get("name", "")
            description = external_issue.get("notes") or ""
            assignee_obj = external_issue.get("assignee")
            assignee = assignee_obj.get("name", "") if assignee_obj else ""
            labels = []
            external_url = external_issue.get("permalink_url") or ""
            external_project_id = ""
            priority = "medium"

        row: dict[str, Any] = {
            "user_id": user_id,
            "external_id": external_id,
            "provider": provider,
            "external_project_id": external_project_id,
            "title": title or "Untitled",
            "description": description,
            "status": pikar_status,
            "priority": priority,
            "assignee": assignee,
            "labels": labels,
            "external_url": external_url,
            "metadata": {
                "raw": {
                    k: v
                    for k, v in external_issue.items()
                    if k not in {"description", "notes"}
                }
            },
        }

        result = await execute_async(
            admin.client.table("synced_tasks").upsert(
                row,
                on_conflict="user_id,provider,external_id",
            ),
            op_name="pm_sync.sync_from_external.upsert",
        )

        # Set skip flag so our own DB write does not echo back
        await self._set_skip_flag(provider, external_id)

        synced_row: dict[str, Any] = result.data[0] if result.data else row
        logger.info(
            "pm_sync.sync_from_external: user=%s provider=%s external_id=%s status=%s",
            user_id,
            provider,
            external_id,
            pikar_status,
        )
        return synced_row

    # ------------------------------------------------------------------
    # Bidirectional sync: Pikar → external
    # ------------------------------------------------------------------

    async def sync_to_external(
        self,
        user_id: str,
        task_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Push updates from a Pikar synced_task to its external PM tool.

        Sets the Redis skip flag before making the API call to prevent
        the resulting webhook event from being re-imported.

        Args:
            user_id: The owning user's UUID.
            task_id: Pikar ``synced_tasks`` row UUID.
            updates: Dict of fields to update.  Accepted keys:
                ``title``, ``description``, ``status``, ``priority``.

        Returns:
            Result dict from the provider API call.

        Raises:
            ValueError: If the task is not found or has no external ID.
        """
        admin = AdminService()

        # Read the synced task
        result = await execute_async(
            admin.client.table("synced_tasks")
            .select("*")
            .eq("id", task_id)
            .eq("user_id", user_id)
            .limit(1),
            op_name="pm_sync.sync_to_external.read",
        )
        if not result.data:
            raise ValueError(f"synced_task {task_id} not found for user {user_id}")

        task = result.data[0]
        provider = task["provider"]
        external_id = task["external_id"]

        # Set skip flag before outbound API call
        await self._set_skip_flag(provider, external_id)

        if provider == "linear":
            from app.services.linear_service import LinearService

            linear_svc = LinearService()

            # Map status to external state_id if status is being updated
            state_id: str | None = None
            if "status" in updates:
                state_id = await self.map_pikar_to_external(
                    user_id, provider, updates["status"]
                )

            # Map priority string to Linear int
            priority_int: int | None = None
            if "priority" in updates:
                priority_str_map = {
                    "none": 0,
                    "urgent": 1,
                    "high": 2,
                    "medium": 3,
                    "low": 4,
                }
                priority_int = priority_str_map.get(updates.get("priority", ""), None)

            api_result = await linear_svc.update_issue(
                user_id=user_id,
                issue_id=external_id,
                title=updates.get("title"),
                description=updates.get("description"),
                state_id=state_id,
                priority=priority_int,
            )

        elif provider == "asana":
            from app.services.asana_service import AsanaService

            asana_svc = AsanaService()

            # Determine completed flag from status
            completed: bool | None = None
            if "status" in updates:
                completed = updates["status"] in ("completed", "cancelled")

            api_result = await asana_svc.update_task(
                user_id=user_id,
                task_id=external_id,
                name=updates.get("title"),
                notes=updates.get("description"),
                completed=completed,
            )

            # If status changed, also move the task to the correct section
            if "status" in updates:
                section_id = await self.map_pikar_to_external(
                    user_id, provider, updates["status"]
                )
                if section_id:
                    await asana_svc.move_task_to_section(
                        user_id=user_id,
                        section_id=section_id,
                        task_id=external_id,
                    )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        logger.info(
            "pm_sync.sync_to_external: user=%s provider=%s external_id=%s",
            user_id,
            provider,
            external_id,
        )
        return api_result

    # ------------------------------------------------------------------
    # Initial bulk sync
    # ------------------------------------------------------------------

    async def initial_sync(
        self,
        user_id: str,
        provider: str,
        project_ids: list[str],
    ) -> dict[str, Any]:
        """Bulk-import tasks from the external PM tool into synced_tasks.

        Fetches issues/tasks updated in the last 30 days for each project
        and calls ``sync_from_external`` for each.

        Args:
            user_id: The owning user's UUID.
            provider: Provider key (``"linear"`` or ``"asana"``).
            project_ids: List of external project/team IDs to sync.

        Returns:
            ``{"synced": N, "errors": N}`` counts.
        """
        synced = 0
        errors = 0

        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=30)).isoformat()

        for project_id in project_ids:
            try:
                if provider == "linear":
                    from app.services.linear_service import LinearService

                    linear_svc = LinearService()
                    issues = await linear_svc.list_issues(
                        user_id=user_id,
                        team_id=project_id,
                        updated_after=cutoff,
                    )
                else:
                    from app.services.asana_service import AsanaService

                    asana_svc = AsanaService()
                    issues = await asana_svc.list_tasks(
                        user_id=user_id,
                        project_id=project_id,
                        modified_since=cutoff,
                    )
            except Exception:
                logger.exception(
                    "initial_sync: fetch failed user=%s provider=%s project=%s",
                    user_id,
                    provider,
                    project_id,
                )
                errors += 1
                continue

            for issue in issues:
                try:
                    # Tag external_project_id before syncing
                    if provider == "linear":
                        issue["_team_id"] = project_id
                    else:
                        issue["_project_id"] = project_id

                    await self.sync_from_external(user_id, provider, issue)
                    synced += 1
                except Exception:
                    logger.exception(
                        "initial_sync: record failed user=%s provider=%s",
                        user_id,
                        provider,
                    )
                    errors += 1

        logger.info(
            "initial_sync complete: user=%s provider=%s synced=%d errors=%d",
            user_id,
            provider,
            synced,
            errors,
        )
        return {"synced": synced, "errors": errors}

    # ------------------------------------------------------------------
    # Sync config persistence
    # ------------------------------------------------------------------

    async def get_sync_config(self, user_id: str, provider: str) -> dict[str, Any]:
        """Read the sync config (selected project IDs) from sync state.

        Args:
            user_id: The owning user's UUID.
            provider: Provider key.

        Returns:
            Dict with ``project_ids`` list and optional cursor metadata.
        """
        mgr = IntegrationManager()
        state = await mgr.get_sync_state(user_id, provider)
        if not state:
            return {"project_ids": []}
        cursor = state.get("sync_cursor") or {}
        return {
            "project_ids": cursor.get("project_ids", []),
            "last_sync_at": state.get("last_sync_at"),
        }

    async def save_sync_config(
        self,
        user_id: str,
        provider: str,
        project_ids: list[str],
    ) -> dict[str, Any]:
        """Persist sync config, seed status mappings, and trigger initial sync.

        Saves the project IDs to ``integration_sync_state.sync_cursor``
        as JSONB, then seeds default status mappings for each project's
        workflow states/sections, then triggers an initial bulk sync for
        all projects.

        Args:
            user_id: The owning user's UUID.
            provider: Provider key.
            project_ids: List of external project/team IDs to enable sync for.

        Returns:
            Initial sync result dict (``{"synced": N, "errors": N}``).
        """
        mgr = IntegrationManager()

        # Persist project IDs in sync cursor
        await mgr.update_sync_state(
            user_id=user_id,
            provider=provider,
            sync_cursor={"project_ids": project_ids},
        )

        # Seed status mappings from all workflow states/sections
        for project_id in project_ids:
            try:
                if provider == "linear":
                    from app.services.linear_service import LinearService

                    linear_svc = LinearService()
                    states = await linear_svc.list_workflow_states(
                        user_id=user_id, team_id=project_id
                    )
                    await self.seed_status_mappings(user_id, provider, states)
                else:
                    from app.services.asana_service import AsanaService

                    asana_svc = AsanaService()
                    sections = await asana_svc.list_sections(
                        user_id=user_id, project_id=project_id
                    )
                    await self.seed_status_mappings(user_id, provider, sections)
            except Exception:
                logger.warning(
                    "save_sync_config: failed to seed mappings for "
                    "user=%s provider=%s project=%s",
                    user_id,
                    provider,
                    project_id,
                )

        # Trigger initial bulk sync
        sync_result = await self.initial_sync(
            user_id=user_id,
            provider=provider,
            project_ids=project_ids,
        )

        # Register webhooks for real-time updates
        try:
            await self.register_webhooks(
                user_id=user_id,
                provider=provider,
                project_ids=project_ids,
            )
        except Exception:
            logger.warning(
                "save_sync_config: webhook registration failed for "
                "user=%s provider=%s — real-time sync will be unavailable",
                user_id,
                provider,
            )

        # Record last sync timestamp
        await mgr.update_sync_state(
            user_id=user_id,
            provider=provider,
            last_sync_at=datetime.now(tz=timezone.utc).isoformat(),
            error_count=sync_result.get("errors", 0),
        )

        return sync_result

    # ------------------------------------------------------------------
    # Webhook subscription lifecycle
    # ------------------------------------------------------------------

    async def register_webhooks(
        self,
        user_id: str,
        provider: str,
        project_ids: list[str],
    ) -> dict[str, Any]:
        """Register webhook subscriptions for real-time PM sync.

        For **Linear**: webhooks are registered at the app level in the
        Linear dashboard — not per-project via API.  This method simply
        verifies that ``LINEAR_WEBHOOK_SECRET`` is configured and logs a
        reminder if it is not.

        For **Asana**: registers a webhook subscription for each project
        via the Asana REST API (``POST /webhooks``).  The webhook GIDs
        returned by Asana are persisted in ``integration_sync_state``
        ``sync_cursor.webhook_gids`` for later cleanup.

        Args:
            user_id: The owning user's UUID.
            provider: Provider key (``"linear"`` or ``"asana"``).
            project_ids: List of external project/team IDs to register
                webhooks for.

        Returns:
            ``{"registered": N}`` where N is the count of newly registered
            webhooks (0 for Linear).
        """
        import os

        registered = 0

        if provider == "linear":
            # Linear uses app-level webhooks configured in the Linear app
            # settings — no API call needed here.
            if not os.environ.get("LINEAR_WEBHOOK_SECRET"):
                logger.warning(
                    "LINEAR_WEBHOOK_SECRET is not set. "
                    "Real-time Linear sync will not be available until "
                    "a webhook is configured in the Linear app settings "
                    "pointing to /webhooks/linear with a signing secret."
                )
            else:
                logger.info(
                    "Linear webhook: app-level webhook configured "
                    "(LINEAR_WEBHOOK_SECRET is set)"
                )
            return {"registered": 0}

        # Asana: register per-project webhooks
        import httpx

        base_url = os.environ.get(
            "PIKAR_BASE_URL",
            os.environ.get("NEXT_PUBLIC_API_URL", ""),
        ).rstrip("/")
        if not base_url:
            logger.warning(
                "register_webhooks: PIKAR_BASE_URL not set — "
                "cannot register Asana webhooks (no target URL)"
            )
            return {"registered": 0}

        from app.services.asana_service import AsanaService

        asana_svc = AsanaService()
        try:
            token = await asana_svc._get_token(user_id)
        except ValueError:
            logger.warning("register_webhooks: no Asana token for user=%s", user_id)
            return {"registered": 0}

        target_url = f"{base_url}/webhooks/asana"
        webhook_gids: list[str] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for project_id in project_ids:
                try:
                    resp = await client.post(
                        "https://app.asana.com/api/1.0/webhooks",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "data": {
                                "resource": project_id,
                                "target": target_url,
                                "filters": [
                                    {
                                        "resource_type": "task",
                                        "action": "changed",
                                    },
                                    {
                                        "resource_type": "task",
                                        "action": "added",
                                    },
                                ],
                            }
                        },
                    )
                    if resp.status_code in (200, 201):
                        webhook_data = resp.json().get("data", {})
                        gid = webhook_data.get("gid", "")
                        if gid:
                            webhook_gids.append(gid)
                            registered += 1
                            logger.info(
                                "Asana webhook registered: project=%s gid=%s",
                                project_id,
                                gid,
                            )
                    else:
                        logger.warning(
                            "Asana webhook registration failed: project=%s "
                            "status=%s body=%s",
                            project_id,
                            resp.status_code,
                            resp.text[:200],
                        )
                except Exception:
                    logger.exception(
                        "register_webhooks: Asana request failed for project=%s",
                        project_id,
                    )

        # Persist webhook GIDs in sync_cursor for cleanup
        if webhook_gids:
            mgr = IntegrationManager()
            state = await mgr.get_sync_state(user_id, provider)
            existing_cursor = {}
            if state:
                existing_cursor = state.get("sync_cursor") or {}

            all_gids = list(set(existing_cursor.get("webhook_gids", []) + webhook_gids))
            existing_cursor["webhook_gids"] = all_gids

            await mgr.update_sync_state(
                user_id=user_id,
                provider=provider,
                sync_cursor=existing_cursor,
            )

        return {"registered": registered}

    async def unregister_webhooks(self, user_id: str, provider: str) -> None:
        """Unregister webhook subscriptions when sync is disabled.

        For **Linear**: no-op — webhooks are managed at the app level.

        For **Asana**: reads the stored webhook GIDs from
        ``integration_sync_state`` and issues ``DELETE /webhooks/{gid}``
        for each one.

        Args:
            user_id: The owning user's UUID.
            provider: Provider key (``"linear"`` or ``"asana"``).
        """
        if provider == "linear":
            # Linear webhooks are app-level; cannot be unregistered via API
            return

        mgr = IntegrationManager()
        state = await mgr.get_sync_state(user_id, provider)
        if not state:
            return

        cursor = state.get("sync_cursor") or {}
        webhook_gids: list[str] = cursor.get("webhook_gids", [])
        if not webhook_gids:
            return

        import httpx

        from app.services.asana_service import AsanaService

        asana_svc = AsanaService()
        try:
            token = await asana_svc._get_token(user_id)
        except ValueError:
            logger.warning("unregister_webhooks: no Asana token for user=%s", user_id)
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            for gid in webhook_gids:
                try:
                    resp = await client.delete(
                        f"https://app.asana.com/api/1.0/webhooks/{gid}",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if resp.status_code in (200, 204):
                        logger.info("Asana webhook deleted: gid=%s", gid)
                    else:
                        logger.warning(
                            "Asana webhook delete failed: gid=%s status=%s",
                            gid,
                            resp.status_code,
                        )
                except Exception:
                    logger.exception(
                        "unregister_webhooks: Asana delete request failed for gid=%s",
                        gid,
                    )

        # Clear webhook GIDs from sync cursor
        cursor["webhook_gids"] = []
        await mgr.update_sync_state(
            user_id=user_id,
            provider=provider,
            sync_cursor=cursor,
        )

    async def handle_webhook_event(
        self,
        provider: str,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Centralised webhook event processor.

        For **Linear**: normalises the issue payload from the webhook
        body and calls ``sync_from_external``.

        For **Asana**: the webhook only delivers task GIDs, so this
        method fetches the full task via the Asana API before calling
        ``sync_from_external``.  The ``event_data`` dict must include
        ``task_gid`` and ``user_id``.

        Args:
            provider: Provider key (``"linear"`` or ``"asana"``).
            event_data: Provider-specific event dict.
                Linear: normalised issue dict (same shape as
                    ``LinearService.list_issues`` response items).
                Asana: ``{"task_gid": str, "user_id": str}``

        Returns:
            The upserted ``synced_tasks`` row, or ``{}`` on skip.

        Raises:
            ValueError: If required fields are missing.
        """
        if provider == "linear":
            # Linear payload is already a normalised issue dict
            user_id = event_data.get("user_id", "")
            if not user_id:
                raise ValueError(
                    "handle_webhook_event: user_id required for linear events"
                )
            return await self.sync_from_external(user_id, provider, event_data)

        # Asana: fetch full task data using the GID
        task_gid = event_data.get("task_gid", "")
        user_id = event_data.get("user_id", "")
        if not task_gid or not user_id:
            raise ValueError(
                "handle_webhook_event: task_gid and user_id required for asana events"
            )

        from app.services.asana_service import AsanaService

        asana_svc = AsanaService()
        try:
            task = await asana_svc.get_task(user_id=user_id, task_gid=task_gid)
        except Exception:
            logger.exception(
                "handle_webhook_event: failed to fetch Asana task %s", task_gid
            )
            return {}

        if not task:
            logger.warning("handle_webhook_event: Asana task %s not found", task_gid)
            return {}

        return await self.sync_from_external(user_id, provider, task)


__all__ = ["PMSyncService"]
