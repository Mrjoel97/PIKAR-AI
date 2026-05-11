"""Workflow template versioning helpers — Phase 110 Plan 02.

Isolated from app/workflows/engine.py to keep the two-table transactional
logic (workflow_template_versions writes + workflow_templates.current_version_id
pointer updates) out of the ~1700-line engine blob. Plan 02 routes call into
here directly.

Public surface:

- :class:`WorkflowTemplateVersion` — Pydantic model mirroring the
  workflow_template_versions row shape. Returned by save / revert.
- :class:`HistoryItem` — lighter projection used by the GET /history endpoint
  (no graph_* fields; just metadata).
- :func:`save_template_version` — async helper that calls the
  ``save_workflow_template_version`` Postgres function. Returns None on stale
  If-Match (the router translates this to HTTP 412 Precondition Failed).
- :func:`list_template_history` — async helper that selects the version rows
  for a template ordered by version_number DESC.
- :func:`revert_template_to_version` — reads the target version's graph_*,
  then calls :func:`save_template_version` with ``parent_version_id`` set to
  the target's id so the new version's parent points at the reverted-to row.
- :func:`copy_seed_template_for_user` — for the seed-fork-on-Edit flow
  (decision 3): inserts a private workflow_templates row with
  ``created_by=user_id``, bootstraps a v1 version row with the seed's
  current graph, returns ``{copied_template_id, seed_name}`` so the PUT
  handler can build the 409 SeedForkResponse body (W-4 contract).

All helpers use the canonical ``get_async_client()`` getter from
``app.services.supabase_client`` (NOT the deprecated ``supabase`` shim) and
await the supabase AsyncClient query builders directly.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from app.services.supabase_client import get_async_client

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Pydantic models
# ----------------------------------------------------------------------------


class WorkflowTemplateVersion(BaseModel):
    """A single row from workflow_template_versions.

    Mirrors the table shape declared in
    ``supabase/migrations/20260615000000_workflow_template_versioning.sql``.
    Returned by :func:`save_template_version` and
    :func:`revert_template_to_version`. The router echoes
    ``saved_at`` as the canonical ETag value (quoted ISO8601).
    """

    id: str
    template_id: str
    version_number: int
    parent_version_id: str | None = None
    graph_nodes: list[dict[str, Any]]
    graph_edges: list[dict[str, Any]]
    graph_layout: dict[str, Any] | None = None
    saved_by_user_id: str | None = None
    saved_at: str
    comment: str | None = None


class HistoryItem(BaseModel):
    """Lighter projection used by GET /workflows/templates/{id}/history.

    Excludes graph_* fields (the version graph is fetched only when the user
    selects/reverts a specific version). ``saved_by_user_name`` is best-effort
    — a JOIN to auth.users that gracefully degrades to None when the auth
    table is not readable or the user has been deleted.
    """

    version_number: int
    version_id: str
    saved_at: str
    saved_by_user_id: str | None = None
    saved_by_user_name: str | None = None
    comment: str | None = None


# ----------------------------------------------------------------------------
# save_template_version()
# ----------------------------------------------------------------------------


async def save_template_version(
    *,
    template_id: str,
    user_id: str,
    graph_nodes: list[dict[str, Any]],
    graph_edges: list[dict[str, Any]],
    graph_layout: dict[str, Any] | None,
    comment: str | None,
    if_match_saved_at: str | None,
    parent_version_id: str | None = None,
) -> WorkflowTemplateVersion | None:
    """Call the ``save_workflow_template_version`` Postgres function.

    Returns the new version row, or None when the server-side If-Match check
    fails (stale write). The router translates None to HTTP 412 Precondition
    Failed with a fresh template body + fresh ETag.

    Args:
        template_id: workflow_templates.id being saved under.
        user_id: auth.uid() of the saving user (written to saved_by_user_id).
        graph_nodes: JSONB array of node definitions.
        graph_edges: JSONB array of edge definitions.
        graph_layout: JSONB dict of layout positions (None allowed).
        comment: optional Save message.
        if_match_saved_at: caller's last-known saved_at for optimistic locking.
            None disables the check (first save / unconditional).
        parent_version_id: explicit override for the revert flow. When None,
            the server function uses the current version's id (normal save chain).
    """
    client = await get_async_client()
    res = await client.rpc(
        "save_workflow_template_version",
        {
            "p_template_id": template_id,
            "p_user_id": user_id,
            "p_graph_nodes": graph_nodes,
            "p_graph_edges": graph_edges,
            "p_graph_layout": graph_layout,
            "p_comment": comment,
            "p_if_match_saved_at": if_match_saved_at,
            "p_parent_version_id": parent_version_id,
        },
    ).execute()

    if not res.data:
        # Zero rows = If-Match mismatch; caller translates to HTTP 412.
        return None
    return WorkflowTemplateVersion(**res.data[0])


# ----------------------------------------------------------------------------
# list_template_history()
# ----------------------------------------------------------------------------


async def list_template_history(template_id: str) -> list[HistoryItem]:
    """Return all version rows for ``template_id``, newest first.

    Best-effort: ``saved_by_user_name`` resolution via auth.users JOIN is
    intentionally NOT attempted here — the supabase admin auth views are
    inconsistently exposed across environments. The frontend can resolve
    names from a separate lookup if needed; for now the field is always None.
    """
    client = await get_async_client()
    res = await (
        client.table("workflow_template_versions")
        .select(
            "id, version_number, saved_at, saved_by_user_id, comment"
        )
        .eq("template_id", template_id)
        .order("version_number", desc=True)
        .execute()
    )

    rows = res.data or []
    history: list[HistoryItem] = []
    for row in rows:
        history.append(
            HistoryItem(
                version_number=row["version_number"],
                version_id=row["id"],
                saved_at=row["saved_at"],
                saved_by_user_id=row.get("saved_by_user_id"),
                saved_by_user_name=None,  # best-effort; resolved client-side if needed
                comment=row.get("comment"),
            )
        )
    return history


# ----------------------------------------------------------------------------
# revert_template_to_version()
# ----------------------------------------------------------------------------


async def revert_template_to_version(
    *,
    template_id: str,
    version_id: str,
    user_id: str,
    if_match_saved_at: str,
) -> WorkflowTemplateVersion | None:
    """Create a NEW version whose graph_* is copied from ``version_id``.

    The new version's ``parent_version_id`` is set to ``version_id`` (the
    target being reverted-to, NOT the current version) so the history graph
    encodes the "branch" in the revert UI.

    Returns the new version row, or None when:
      - the target version does not exist (caller translates to 404), or
      - the If-Match check fails (caller translates to 412).
    """
    client = await get_async_client()

    # Load the target version row to read its graph_*.
    target_res = await (
        client.table("workflow_template_versions")
        .select("id, template_id, graph_nodes, graph_edges, graph_layout")
        .eq("id", version_id)
        .eq("template_id", template_id)
        .limit(1)
        .execute()
    )
    rows = target_res.data or []
    if not rows:
        # Target version doesn't exist (or belongs to a different template).
        return None
    target = rows[0]

    # Defer to save_template_version, passing parent_version_id=version_id so
    # the new version's parent points at the reverted-TO row.
    return await save_template_version(
        template_id=template_id,
        user_id=user_id,
        graph_nodes=target["graph_nodes"],
        graph_edges=target["graph_edges"],
        graph_layout=target.get("graph_layout"),
        comment=f"Reverted to v{target.get('version_number', '?')}",
        if_match_saved_at=if_match_saved_at,
        parent_version_id=version_id,
    )


# ----------------------------------------------------------------------------
# copy_seed_template_for_user()
# ----------------------------------------------------------------------------


async def copy_seed_template_for_user(
    *,
    seed_template_id: str,
    user_id: str,
) -> dict[str, Any]:
    """For decision 3: clicking Edit on a seed (``created_by IS NULL``) creates
    a private copy in the calling user's namespace.

    Returns a dict ``{"copied_template_id": <uuid>, "seed_name": <name>}`` so
    the caller (PUT handler) can build the 409 SeedForkResponse body (W-4
    contract — must include both keys for the frontend's CopyForkError toast).

    Also bootstraps a v1 ``workflow_template_versions`` row with the seed's
    current ``graph_nodes`` / ``graph_edges`` / ``graph_layout`` so the user
    lands on a sane initial state when they reload the editor at the new URL.

    Raises:
        ValueError: when the source template's ``created_by`` is NOT NULL
            (caller passed a non-seed template id), or when the source
            template does not exist at all.
    """
    client = await get_async_client()

    # 1. Load the seed row.
    seed_res = await (
        client.table("workflow_templates")
        .select(
            "id, name, description, category, template_key, version, "
            "lifecycle_status, personas_allowed, created_by, "
            "graph_nodes, graph_edges, graph_layout, current_version_id"
        )
        .eq("id", seed_template_id)
        .limit(1)
        .execute()
    )
    rows = seed_res.data or []
    if not rows:
        raise ValueError(
            f"seed template {seed_template_id} not found"
        )
    seed = rows[0]
    if seed.get("created_by") is not None:
        # Source is a private template, not a seed — caller used the wrong API.
        raise ValueError(
            f"template {seed_template_id} is not a seed (created_by IS NOT NULL)"
        )

    seed_name = seed.get("name") or "Untitled Seed"

    # 2. Insert the private copy.
    new_template_res = await (
        client.table("workflow_templates")
        .insert(
            {
                "name": seed_name,
                "description": seed.get("description") or "",
                "category": seed.get("category") or "custom",
                "template_key": seed.get("template_key"),
                "version": seed.get("version") or 1,
                "lifecycle_status": "draft",
                "personas_allowed": seed.get("personas_allowed"),
                "created_by": user_id,
                "graph_nodes": seed.get("graph_nodes"),
                "graph_edges": seed.get("graph_edges"),
                "graph_layout": seed.get("graph_layout"),
            }
        )
        .execute()
    )
    new_rows = new_template_res.data or []
    if not new_rows:
        raise RuntimeError(
            "Failed to insert workflow_templates copy row for seed-fork flow"
        )
    new_template = new_rows[0]
    copied_template_id = new_template["id"]

    # 3. Bootstrap a v1 workflow_template_versions row by calling the Save RPC.
    #    If-Match=None so it's an unconditional first save.
    bootstrap_version = await save_template_version(
        template_id=copied_template_id,
        user_id=user_id,
        graph_nodes=seed.get("graph_nodes") or [],
        graph_edges=seed.get("graph_edges") or [],
        graph_layout=seed.get("graph_layout"),
        comment=f"Forked from seed '{seed_name}' on first Edit",
        if_match_saved_at=None,
    )
    if bootstrap_version is None:
        # The RPC should never fail on an unconditional first save unless
        # the template row was deleted between insert and RPC — log + raise.
        raise RuntimeError(
            "Bootstrap v1 version write returned no rows for copied template "
            f"{copied_template_id}"
        )

    return {
        "copied_template_id": copied_template_id,
        "seed_name": seed_name,
    }
