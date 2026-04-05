# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""LinearService -- Linear GraphQL API client.

Provides:
- Team and issue listing from Linear via GraphQL
- Issue creation and updates (bidirectional sync)
- Workflow state listing for status mapping

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

_LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
_TIMEOUT = 30.0


class LinearService(BaseService):
    """Linear GraphQL API client for bidirectional task sync.

    All methods require a ``user_id`` to resolve the OAuth access token
    via ``IntegrationManager``.  The token is fetched fresh for each
    call (with automatic refresh if expiring).

    Args:
        user_token: User JWT for Supabase RLS (passed to BaseService).
    """

    # ------------------------------------------------------------------
    # Internal GraphQL helper
    # ------------------------------------------------------------------

    async def _graphql(
        self,
        user_id: str,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query or mutation against the Linear API.

        Fetches the OAuth access token via ``IntegrationManager``, then
        POSTs the query to the Linear GraphQL endpoint.

        Args:
            user_id: The owning user's UUID.
            query: GraphQL query or mutation string.
            variables: Optional variables dict for the operation.

        Returns:
            The ``data`` field from the GraphQL response.

        Raises:
            ValueError: If the user has no Linear connection.
            RuntimeError: If the API returns GraphQL errors.
        """
        import httpx

        mgr = IntegrationManager()
        token = await mgr.get_valid_token(user_id, "linear")
        if not token:
            raise ValueError(
                f"No Linear connection found for user {user_id}. "
                "Please connect Linear in Settings > Integrations."
            )

        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                _LINEAR_GRAPHQL_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            result = response.json()

        errors = result.get("errors")
        if errors:
            messages = "; ".join(e.get("message", "unknown") for e in errors)
            logger.error(
                "Linear GraphQL errors for user=%s: %s", user_id, messages
            )
            raise RuntimeError(f"Linear API error: {messages}")

        return result.get("data") or {}

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------

    async def list_teams(self, user_id: str) -> list[dict[str, Any]]:
        """List all Linear teams the user has access to.

        Args:
            user_id: The owning user's UUID.

        Returns:
            List of team dicts with ``id``, ``name``, ``key``,
            ``description``.
        """
        query = """
        query {
            teams {
                nodes {
                    id
                    name
                    key
                    description
                }
            }
        }
        """
        data = await self._graphql(user_id, query)
        nodes: list[dict[str, Any]] = (
            data.get("teams", {}).get("nodes") or []
        )
        logger.info(
            "Linear list_teams: user=%s found=%d", user_id, len(nodes)
        )
        return nodes

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    async def list_issues(
        self,
        user_id: str,
        team_id: str,
        updated_after: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List issues for a team, optionally filtered by update time.

        Paginates through all issues using the GraphQL ``after`` cursor.
        Each page requests up to ``limit`` items.

        Args:
            user_id: The owning user's UUID.
            team_id: Linear team UUID.
            updated_after: ISO-8601 timestamp; only return issues updated
                after this time. Used for incremental sync.
            limit: Page size (default 100).

        Returns:
            List of issue dicts with ``id``, ``identifier``, ``title``,
            ``description``, ``state``, ``priority``, ``assignee``,
            ``labels``, ``url``, ``updatedAt``.
        """
        filter_vars: dict[str, Any] = {
            "teamId": team_id,
            "first": limit,
        }

        if updated_after:
            filter_vars["updatedAfter"] = updated_after
            query = """
            query ListIssues($teamId: String!, $first: Int!,
                             $after: String, $updatedAfter: DateComparator) {
                issues(
                    filter: {
                        team: { id: { eq: $teamId } }
                        updatedAt: { gte: $updatedAfter }
                    }
                    first: $first
                    after: $after
                ) {
                    nodes {
                        id
                        identifier
                        title
                        description
                        state { id name type }
                        priority
                        assignee { name }
                        labels { nodes { name } }
                        url
                        updatedAt
                    }
                    pageInfo { hasNextPage endCursor }
                }
            }
            """
        else:
            query = """
            query ListIssues($teamId: String!, $first: Int!, $after: String) {
                issues(
                    filter: { team: { id: { eq: $teamId } } }
                    first: $first
                    after: $after
                ) {
                    nodes {
                        id
                        identifier
                        title
                        description
                        state { id name type }
                        priority
                        assignee { name }
                        labels { nodes { name } }
                        url
                        updatedAt
                    }
                    pageInfo { hasNextPage endCursor }
                }
            }
            """

        all_issues: list[dict[str, Any]] = []
        after: str | None = None

        while True:
            vars_with_cursor: dict[str, Any] = {**filter_vars, "after": after}
            data = await self._graphql(user_id, query, vars_with_cursor)
            issues_data = data.get("issues", {})
            nodes = issues_data.get("nodes") or []
            all_issues.extend(nodes)

            page_info = issues_data.get("pageInfo", {})
            if page_info.get("hasNextPage") and page_info.get("endCursor"):
                after = page_info["endCursor"]
            else:
                break

        logger.info(
            "Linear list_issues: user=%s team=%s found=%d",
            user_id,
            team_id,
            len(all_issues),
        )
        return all_issues

    async def create_issue(
        self,
        user_id: str,
        team_id: str,
        title: str,
        description: str = "",
        priority: int = 0,
        state_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new issue in Linear.

        Args:
            user_id: The owning user's UUID.
            team_id: Linear team UUID.
            title: Issue title.
            description: Issue description (Markdown, optional).
            priority: Priority integer (0=None, 1=Urgent, 2=High, 3=Medium, 4=Low).
            state_id: Optional workflow state UUID.

        Returns:
            The created issue dict.

        Raises:
            RuntimeError: If issue creation fails.
        """
        query = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    description
                    state { id name type }
                    priority
                    url
                    updatedAt
                }
            }
        }
        """
        input_data: dict[str, Any] = {
            "teamId": team_id,
            "title": title,
            "description": description,
            "priority": priority,
        }
        if state_id:
            input_data["stateId"] = state_id

        data = await self._graphql(user_id, query, {"input": input_data})
        result = data.get("issueCreate", {})
        if not result.get("success"):
            raise RuntimeError("Linear issueCreate returned success=false")

        issue = result.get("issue") or {}
        logger.info(
            "Linear create_issue: user=%s team=%s id=%s",
            user_id,
            team_id,
            issue.get("id"),
        )
        return issue

    async def update_issue(
        self,
        user_id: str,
        issue_id: str,
        title: str | None = None,
        description: str | None = None,
        state_id: str | None = None,
        priority: int | None = None,
    ) -> dict[str, Any]:
        """Update an existing Linear issue.

        Only fields with non-None values are included in the update.

        Args:
            user_id: The owning user's UUID.
            issue_id: Linear issue UUID.
            title: New title, or ``None`` to leave unchanged.
            description: New description, or ``None`` to leave unchanged.
            state_id: New workflow state UUID, or ``None`` to leave unchanged.
            priority: New priority integer, or ``None`` to leave unchanged.

        Returns:
            The updated issue dict.

        Raises:
            RuntimeError: If the update fails.
        """
        query = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    description
                    state { id name type }
                    priority
                    url
                    updatedAt
                }
            }
        }
        """
        input_data: dict[str, Any] = {}
        if title is not None:
            input_data["title"] = title
        if description is not None:
            input_data["description"] = description
        if state_id is not None:
            input_data["stateId"] = state_id
        if priority is not None:
            input_data["priority"] = priority

        data = await self._graphql(
            user_id, query, {"id": issue_id, "input": input_data}
        )
        result = data.get("issueUpdate", {})
        if not result.get("success"):
            raise RuntimeError("Linear issueUpdate returned success=false")

        issue = result.get("issue") or {}
        logger.info(
            "Linear update_issue: user=%s issue=%s", user_id, issue_id
        )
        return issue

    # ------------------------------------------------------------------
    # Workflow States
    # ------------------------------------------------------------------

    async def list_workflow_states(
        self, user_id: str, team_id: str
    ) -> list[dict[str, Any]]:
        """List workflow states for a team, sorted by position.

        Used to populate the status mapping UI.

        Args:
            user_id: The owning user's UUID.
            team_id: Linear team UUID.

        Returns:
            List of state dicts with ``id``, ``name``, ``type``,
            ``position``, sorted ascending by position.
        """
        query = """
        query ListWorkflowStates($teamId: ID!) {
            workflowStates(
                filter: { team: { id: { eq: $teamId } } }
            ) {
                nodes {
                    id
                    name
                    type
                    position
                }
            }
        }
        """
        data = await self._graphql(user_id, query, {"teamId": team_id})
        nodes: list[dict[str, Any]] = (
            data.get("workflowStates", {}).get("nodes") or []
        )
        nodes.sort(key=lambda s: s.get("position", 0))
        logger.info(
            "Linear list_workflow_states: user=%s team=%s found=%d",
            user_id,
            team_id,
            len(nodes),
        )
        return nodes


__all__ = ["LinearService"]
