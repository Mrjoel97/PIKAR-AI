# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Iteration Service — screen editing, version tracking, and design system injection.

Provides two exported functions:

* ``_get_locked_design_markdown`` — fetches raw_markdown from design_systems if locked.
* ``edit_screen_variant`` — async generator that calls Stitch edit_screens, persists
  assets, inserts a new screen_variants row with incremented iteration, and yields
  SSE-compatible event dicts.

CRITICAL: All Stitch calls are sequential ``await`` calls — never ``asyncio.gather``.
The StitchMCPService serialises calls through an asyncio.Lock; gathering would cause
a deadlock.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from app.services.stitch_assets import persist_screen_assets
from app.services.stitch_mcp import get_stitch_service
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)


async def _get_locked_design_markdown(
    project_id: str,
    user_id: str,
) -> str | None:
    """Return raw_markdown from design_systems if locked; None otherwise.

    Queries the design_systems table for the given project. If the row has
    ``locked=True``, returns its ``raw_markdown`` string. If the row is unlocked
    or does not exist, returns ``None``.

    Args:
        project_id: App project UUID.
        user_id: Authenticated user UUID.

    Returns:
        The raw Markdown design system string, or ``None`` if not locked.
    """
    supabase = get_service_client()
    result = (
        supabase.table("design_systems")
        .select("locked, raw_markdown")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None
    row = rows[0]
    if row.get("locked"):
        return row.get("raw_markdown") or None
    return None


async def edit_screen_variant(
    project_id: str,
    screen_id: str,
    user_id: str,
    stitch_project_id: str,
    stitch_screen_id: str,
    change_description: str,
    design_system_markdown: str | None,
    iteration_number: int,
) -> AsyncIterator[dict[str, Any]]:
    """Apply a natural-language edit to a screen via Stitch edit_screens.

    Builds the prompt (optionally prepending locked design system), calls Stitch,
    falls back to get_screen when html_url is absent, persists assets to Supabase
    Storage, inserts a new screen_variants row, and yields SSE-compatible events.

    Yields SSE-compatible event dicts:

    1. ``{"step": "editing", "message": ...}``
    2. ``{"step": "edit_complete", "variant_id": ..., "screenshot_url": ...,
           "html_url": ..., "iteration": ..., "screen_id": ...}``
    3. ``{"step": "ready", "screen_id": ..., "iteration": ...}``

    Args:
        project_id: App project UUID.
        screen_id: Screen UUID to iterate on.
        user_id: Authenticated user UUID.
        stitch_project_id: Stitch project ID (without 'projects/' prefix).
        stitch_screen_id: Current selected variant's Stitch screen ID.
        change_description: Natural-language description of the desired change.
        design_system_markdown: Locked design system raw_markdown, or None if unlocked.
        iteration_number: The new iteration number for this variant.

    Yields:
        Event dicts suitable for JSON-serialising into SSE data lines.
    """
    supabase = get_service_client()
    service = get_stitch_service()

    # Build prompt — prepend design system when locked
    if design_system_markdown is not None:
        prompt = f"{design_system_markdown}\n\nEdits: {change_description}"
    else:
        prompt = change_description

    yield {
        "step": "editing",
        "message": f"Applying edit: {change_description[:60]}...",
    }

    # Call Stitch edit_screens — selectedScreenIds MUST be a list
    stitch_response = await service.call_tool(
        "edit_screens",
        {
            "projectId": stitch_project_id,
            "prompt": prompt,
            "selectedScreenIds": [stitch_screen_id],
        },
    )

    # Extract new stitch screen id from response
    new_stitch_screen_id = stitch_response.get("screenId") or stitch_response.get(
        "screen_id", stitch_screen_id
    )

    # Fallback: if edit_screens response lacks html_url/htmlUrl, call get_screen
    has_html = stitch_response.get("html_url") or stitch_response.get("htmlUrl")
    if not has_html:
        logger.debug(
            "edit_screens response missing html_url for screen %s — calling get_screen fallback",
            new_stitch_screen_id,
        )
        stitch_response = await service.call_tool(
            "get_screen",
            {
                "name": f"projects/{stitch_project_id}/screens/{new_stitch_screen_id}",
                "projectId": stitch_project_id,
                "screenId": new_stitch_screen_id,
            },
        )

    # Persist assets to Supabase Storage BEFORE yielding
    persisted = await persist_screen_assets(
        stitch_response=stitch_response,
        user_id=user_id,
        project_id=project_id,
        screen_id=screen_id,
        variant_index=iteration_number,
    )

    variant_id = str(uuid4())

    # Deselect all existing variants for this screen
    supabase.table("screen_variants").update({"is_selected": False}).eq(
        "screen_id", screen_id
    ).neq("id", variant_id).execute()

    # Insert new screen_variants row with this iteration
    supabase.table("screen_variants").insert(
        {
            "id": variant_id,
            "screen_id": screen_id,
            "user_id": user_id,
            "variant_index": iteration_number,
            "stitch_screen_id": new_stitch_screen_id,
            "html_url": persisted["html_url"],
            "screenshot_url": persisted["screenshot_url"],
            "prompt_used": change_description,
            "is_selected": True,
            "iteration": iteration_number,
        }
    ).execute()

    yield {
        "step": "edit_complete",
        "variant_id": variant_id,
        "screenshot_url": persisted["screenshot_url"],
        "html_url": persisted["html_url"],
        "iteration": iteration_number,
        "screen_id": screen_id,
    }

    yield {
        "step": "ready",
        "screen_id": screen_id,
        "iteration": iteration_number,
    }
