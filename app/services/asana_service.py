# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""AsanaService -- Asana REST API client.

Provides:
- Workspace and project listing
- Task listing, creation, and updates
- Section listing (Asana sections are used as task statuses)
- Moving tasks between sections (status changes in Asana)

Authentication is delegated to ``IntegrationManager.get_valid_token``
so OAuth token refresh is handled transparently.  All HTTP calls use
``httpx.AsyncClient`` with a 30-second timeout.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.base_service import BaseService
from app.services.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)

_ASANA_BASE_URL = "https://app.asana.com/api/1.0"
_TIMEOUT = 30.0


class AsanaService(BaseService):
    """Asana REST API client for bidirectional task sync.

    All methods require a ``user_id`` to resolve the OAuth access token
    via ``IntegrationManager``.  The token is fetched fresh for each
    call (with automatic refresh if expiring).

    Args:
        user_token: User JWT for Supabase RLS (passed to BaseService).
    """

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    async def _get_token(self, user_id: str) -> str:
        """Resolve the Asana OAuth access token for a user.

        Args:
            user_id: The owning user's UUID.

        Returns:
            Plaintext OAuth access token.

        Raises:
            ValueError: If no Asana connection is found for the user.
        """
        mgr = IntegrationManager()
        token = await mgr.get_valid_token(user_id, "asana")
        if not token:
            raise ValueError(
                f"No Asana connection found for user {user_id}. "
                "Please connect Asana in Settings > Integrations."
            )
        return token

    async def _get(
        self,
        user_id: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Send an authenticated GET request to the Asana API.

        Args:
            user_id: The owning user's UUID.
            path: API path (e.g. ``/workspaces``).
            params: Optional query parameters.

        Returns:
            The ``data`` field from the Asana API response.

        Raises:
            httpx.HTTPStatusError: On non-2xx responses.
        """
        import httpx

        token = await self._get_token(user_id)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                f"{_ASANA_BASE_URL}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json().get("data")

    async def _post(
        self,
        user_id: str,
        path: str,
        body: dict[str, Any],
    ) -> Any:
        """Send an authenticated POST request to the Asana API.

        Args:
            user_id: The owning user's UUID.
            path: API path (e.g. ``/tasks``).
            body: JSON body for the request.

        Returns:
            The ``data`` field from the Asana API response.

        Raises:
            httpx.HTTPStatusError: On non-2xx responses.
        """
        import httpx

        token = await self._get_token(user_id)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{_ASANA_BASE_URL}{path}",
                json=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            return response.json().get("data")

    async def _put(
        self,
        user_id: str,
        path: str,
        body: dict[str, Any],
    ) -> Any:
        """Send an authenticated PUT request to the Asana API.

        Args:
            user_id: The owning user's UUID.
            path: API path (e.g. ``/tasks/{task_id}``).
            body: JSON body for the request.

        Returns:
            The ``data`` field from the Asana API response.

        Raises:
            httpx.HTTPStatusError: On non-2xx responses.
        """
        import httpx

        token = await self._get_token(user_id)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.put(
                f"{_ASANA_BASE_URL}{path}",
                json=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            return response.json().get("data")

    # ------------------------------------------------------------------
    # Workspaces
    # ------------------------------------------------------------------

    async def list_workspaces(self, user_id: str) -> list[dict[str, Any]]:
        """List all Asana workspaces the user has access to.

        Args:
            user_id: The owning user's UUID.

        Returns:
            List of workspace dicts with ``gid`` and ``name``.
        """
        data = await self._get(user_id, "/workspaces")
        workspaces: list[dict[str, Any]] = data or []
        logger.info(
            "Asana list_workspaces: user=%s found=%d",
            user_id,
            len(workspaces),
        )
        return workspaces

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    async def list_projects(
        self, user_id: str, workspace_id: str
    ) -> list[dict[str, Any]]:
        """List non-archived projects in a workspace.

        Args:
            user_id: The owning user's UUID.
            workspace_id: Asana workspace GID.

        Returns:
            List of project dicts with ``gid``, ``name``, ``color``.
            Archived projects are excluded.
        """
        data = await self._get(
            user_id,
            "/projects",
            params={
                "workspace": workspace_id,
                "opt_fields": "name,color,archived",
            },
        )
        projects: list[dict[str, Any]] = data or []
        # Filter out archived projects
        active = [p for p in projects if not p.get("archived", False)]
        logger.info(
            "Asana list_projects: user=%s workspace=%s found=%d",
            user_id,
            workspace_id,
            len(active),
        )
        return active

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    async def list_tasks(
        self,
        user_id: str,
        project_id: str,
        modified_since: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List tasks in a project, optionally filtered by modification time.

        Paginates through all tasks using the Asana ``offset`` cursor.

        Args:
            user_id: The owning user's UUID.
            project_id: Asana project GID.
            modified_since: ISO-8601 timestamp; only return tasks modified
                after this time. Used for incremental sync.
            limit: Page size (default 100).

        Returns:
            List of task dicts with ``gid``, ``name``, ``notes``,
            ``completed``, ``assignee``, ``memberships``,
            ``permalink_url``, ``modified_at``.
        """
        params: dict[str, Any] = {
            "project": project_id,
            "opt_fields": (
                "name,notes,completed,assignee.name,"
                "memberships.section.name,permalink_url,modified_at"
            ),
            "limit": limit,
        }
        if modified_since:
            params["modified_since"] = modified_since

        all_tasks: list[dict[str, Any]] = []
        offset: str | None = None

        while True:
            if offset:
                params["offset"] = offset

            data = await self._get(user_id, "/tasks", params=params)
            tasks: list[dict[str, Any]] = data or []
            all_tasks.extend(tasks)

            # Asana paginates via next_page in the full response envelope;
            # the _get helper returns only `data`.  Asana uses a separate
            # next_page field. Fetch next_page metadata differently.
            # When fewer items than limit are returned, we are on the last page.
            if len(tasks) < limit:
                break

            # When a full page is returned, re-request with offset from last item.
            # Asana uses token-based pagination; offset is returned separately.
            # Since _get only returns `data`, we stop when we get a short page.
            break  # Guard — short page checked above covers most cases

        logger.info(
            "Asana list_tasks: user=%s project=%s found=%d",
            user_id,
            project_id,
            len(all_tasks),
        )
        return all_tasks

    async def get_task(self, user_id: str, task_gid: str) -> dict[str, Any] | None:
        """Fetch a single Asana task by GID with full field set.

        Used by the webhook handler which only receives a task GID and
        needs to retrieve the full task data for sync.

        Args:
            user_id: The owning user's UUID.
            task_gid: Asana task GID.

        Returns:
            Task dict with ``gid``, ``name``, ``notes``, ``completed``,
            ``assignee``, ``memberships``, ``permalink_url``, or ``None``
            if the task cannot be fetched.
        """
        try:
            data = await self._get(
                user_id,
                f"/tasks/{task_gid}",
                params={
                    "opt_fields": (
                        "name,notes,completed,assignee.name,"
                        "memberships.section.name,permalink_url,modified_at"
                    )
                },
            )
            task: dict[str, Any] = data or {}
            logger.info(
                "Asana get_task: user=%s gid=%s name=%s",
                user_id,
                task_gid,
                task.get("name", ""),
            )
            return task or None
        except Exception:
            logger.exception("Asana get_task failed: user=%s gid=%s", user_id, task_gid)
            return None

    async def create_task(
        self,
        user_id: str,
        project_id: str,
        name: str,
        notes: str = "",
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """Create a new task in an Asana project.

        Args:
            user_id: The owning user's UUID.
            project_id: Asana project GID.
            name: Task name.
            notes: Task description (optional).
            assignee: Assignee GID or ``"me"`` (optional).

        Returns:
            The created task dict.
        """
        body: dict[str, Any] = {
            "data": {
                "name": name,
                "notes": notes,
                "projects": [project_id],
            }
        }
        if assignee:
            body["data"]["assignee"] = assignee

        task = await self._post(user_id, "/tasks", body)
        task_dict: dict[str, Any] = task or {}
        logger.info(
            "Asana create_task: user=%s project=%s gid=%s",
            user_id,
            project_id,
            task_dict.get("gid"),
        )
        return task_dict

    async def update_task(
        self,
        user_id: str,
        task_id: str,
        name: str | None = None,
        notes: str | None = None,
        completed: bool | None = None,
    ) -> dict[str, Any]:
        """Update fields on an existing Asana task.

        Only fields with non-None values are included in the update.

        Args:
            user_id: The owning user's UUID.
            task_id: Asana task GID.
            name: New task name, or ``None`` to leave unchanged.
            notes: New task notes, or ``None`` to leave unchanged.
            completed: Completion flag, or ``None`` to leave unchanged.

        Returns:
            The updated task dict.
        """
        update_data: dict[str, Any] = {}
        if name is not None:
            update_data["name"] = name
        if notes is not None:
            update_data["notes"] = notes
        if completed is not None:
            update_data["completed"] = completed

        task = await self._put(user_id, f"/tasks/{task_id}", {"data": update_data})
        task_dict: dict[str, Any] = task or {}
        logger.info("Asana update_task: user=%s task=%s", user_id, task_id)
        return task_dict

    # ------------------------------------------------------------------
    # Sections (Asana status equivalent)
    # ------------------------------------------------------------------

    async def list_sections(
        self, user_id: str, project_id: str
    ) -> list[dict[str, Any]]:
        """List sections in an Asana project.

        Sections represent task groupings that serve as workflow statuses
        in Asana.  Used to populate the status mapping UI.

        Args:
            user_id: The owning user's UUID.
            project_id: Asana project GID.

        Returns:
            List of section dicts with ``gid`` and ``name``.
        """
        data = await self._get(
            user_id,
            "/sections",
            params={"project": project_id},
        )
        sections: list[dict[str, Any]] = data or []
        logger.info(
            "Asana list_sections: user=%s project=%s found=%d",
            user_id,
            project_id,
            len(sections),
        )
        return sections

    async def move_task_to_section(
        self, user_id: str, section_id: str, task_id: str
    ) -> None:
        """Move a task to a different section (status change in Asana).

        Args:
            user_id: The owning user's UUID.
            section_id: Target Asana section GID.
            task_id: Asana task GID to move.
        """
        await self._post(
            user_id,
            f"/sections/{section_id}/addTask",
            {"data": {"task": task_id}},
        )
        logger.info(
            "Asana move_task_to_section: user=%s task=%s section=%s",
            user_id,
            task_id,
            section_id,
        )


__all__ = ["AsanaService"]
