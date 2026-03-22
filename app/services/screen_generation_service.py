"""Screen Generation Service — sequential Stitch MCP calls producing design variants.

Provides two async generators:

* ``generate_screen_variants`` -- creates a DESKTOP app_screens row and sequentially
  calls Stitch 2-3 times, yielding SSE-compatible event dicts between each call.
  Assets are persisted to Supabase Storage before each ``variant_generated`` event
  so callers receive permanent URLs, not short-lived Stitch signed URLs.

* ``generate_device_variant`` — single Stitch call for a MOBILE/TABLET variant of
  an existing screen.

CRITICAL: All Stitch calls are sequential ``await`` calls — never ``asyncio.gather``.
The StitchMCPService serialises calls through an asyncio.Lock; gathering would
cause a deadlock.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any, Literal
from uuid import uuid4

from app.services.stitch_assets import persist_screen_assets
from app.services.stitch_mcp import get_stitch_service
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

DeviceType = Literal["DESKTOP", "MOBILE", "TABLET"]


async def generate_screen_variants(
    project_id: str,
    user_id: str,
    screen_name: str,
    page_slug: str,
    prompt: str,
    stitch_project_id: str,
    num_variants: int = 3,
) -> AsyncIterator[dict[str, Any]]:
    """Generate multiple DESKTOP design variants for a screen via Stitch MCP.

    Yields SSE-compatible event dicts:

    1. ``{"step": "generating", "message": ..., "screen_id": ...}``
    2. N x ``{"step": "variant_generated", "variant_index": i, "variant_id": ...,
               "screenshot_url": ..., "html_url": ..., "screen_id": ...}``
    3. ``{"step": "ready", "screen_id": ..., "variants": [...]}``

    Args:
        project_id: App project UUID.
        user_id: Authenticated user UUID.
        screen_name: Human-readable screen name (e.g. "Home Page").
        page_slug: URL slug matching build_plan page entry (e.g. "home").
        prompt: Generation prompt (should include design system tokens).
        stitch_project_id: Stitch project ID to associate the screen with.
        num_variants: Number of variants to generate (default 3).

    Yields:
        Event dicts suitable for JSON-serialising into SSE data lines.
    """
    supabase = get_service_client()
    service = get_stitch_service()
    screen_id = str(uuid4())

    # Insert the app_screens row (DESKTOP device type)
    supabase.table("app_screens").insert(
        {
            "id": screen_id,
            "project_id": project_id,
            "user_id": user_id,
            "name": screen_name,
            "page_slug": page_slug,
            "device_type": "DESKTOP",
            "order_index": 0,
            "approved": False,
            "stitch_project_id": stitch_project_id,
        }
    ).execute()

    yield {
        "step": "generating",
        "message": f"Generating {screen_name}...",
        "screen_id": screen_id,
    }

    variants_list: list[dict[str, Any]] = []

    for i in range(num_variants):
        # Sequential Stitch call — Lock inside StitchMCPService serialises this
        stitch_response = await service.call_tool(
            "generate_screen_from_text",
            {
                "prompt": prompt,
                "projectId": stitch_project_id,
                "deviceType": "DESKTOP",
            },
        )

        # Persist assets BEFORE yielding — callers must receive permanent URLs
        persisted = await persist_screen_assets(
            stitch_response=stitch_response,
            user_id=user_id,
            project_id=project_id,
            screen_id=screen_id,
            variant_index=i,
        )

        variant_id = str(uuid4())
        stitch_screen_id = stitch_response.get("screenId") or stitch_response.get(
            "screen_id", ""
        )

        # Insert screen_variants row — first variant is selected by default
        supabase.table("screen_variants").insert(
            {
                "id": variant_id,
                "screen_id": screen_id,
                "user_id": user_id,
                "variant_index": i,
                "stitch_screen_id": stitch_screen_id,
                "html_url": persisted["html_url"],
                "screenshot_url": persisted["screenshot_url"],
                "prompt_used": prompt,
                "is_selected": i == 0,
                "iteration": 1,
            }
        ).execute()

        variant_event = {
            "step": "variant_generated",
            "variant_index": i,
            "variant_id": variant_id,
            "screenshot_url": persisted["screenshot_url"],
            "html_url": persisted["html_url"],
            "screen_id": screen_id,
        }
        variants_list.append(variant_event)
        yield variant_event

    yield {
        "step": "ready",
        "screen_id": screen_id,
        "variants": variants_list,
    }


async def generate_device_variant(
    screen_id: str,
    user_id: str,
    prompt: str,
    stitch_project_id: str,
    device_type: DeviceType,
    project_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """Generate a single device-specific variant (MOBILE or TABLET) for an existing screen.

    Creates or finds an ``app_screens`` row for the given ``device_type``, makes a
    single Stitch call with the correct ``deviceType`` argument, persists assets,
    and inserts a ``screen_variants`` row.

    Yields SSE-compatible event dicts:

    1. ``{"step": "generating", "message": ..., "screen_id": ...}``
    2. ``{"step": "device_generated", "device_type": ..., "variant_id": ...,
           "screenshot_url": ..., "html_url": ..., "screen_id": ...}``
    3. ``{"step": "ready", "screen_id": ..., "device_type": ...}``

    Args:
        screen_id: Parent DESKTOP screen UUID (used as reference).
        user_id: Authenticated user UUID.
        prompt: Generation prompt including design system tokens.
        stitch_project_id: Stitch project ID to associate with.
        device_type: Target device — "MOBILE" or "TABLET".
        project_id: App project UUID.

    Yields:
        Event dicts suitable for JSON-serialising into SSE data lines.
    """
    supabase = get_service_client()
    service = get_stitch_service()

    # Create a new device-specific app_screens row
    device_screen_id = str(uuid4())
    supabase.table("app_screens").insert(
        {
            "id": device_screen_id,
            "project_id": project_id,
            "user_id": user_id,
            "name": f"{device_type.capitalize()} variant",
            "device_type": device_type,
            "order_index": 0,
            "approved": False,
            "stitch_project_id": stitch_project_id,
        }
    ).execute()

    yield {
        "step": "generating",
        "message": f"Generating {device_type} variant...",
        "screen_id": device_screen_id,
    }

    # Single Stitch call with the correct deviceType
    stitch_response = await service.call_tool(
        "generate_screen_from_text",
        {
            "prompt": prompt,
            "projectId": stitch_project_id,
            "deviceType": device_type,
        },
    )

    # Persist assets before yielding permanent URLs
    persisted = await persist_screen_assets(
        stitch_response=stitch_response,
        user_id=user_id,
        project_id=project_id,
        screen_id=device_screen_id,
        variant_index=0,
    )

    variant_id = str(uuid4())
    stitch_screen_id = stitch_response.get("screenId") or stitch_response.get(
        "screen_id", ""
    )

    supabase.table("screen_variants").insert(
        {
            "id": variant_id,
            "screen_id": device_screen_id,
            "user_id": user_id,
            "variant_index": 0,
            "stitch_screen_id": stitch_screen_id,
            "html_url": persisted["html_url"],
            "screenshot_url": persisted["screenshot_url"],
            "prompt_used": prompt,
            "is_selected": True,
            "iteration": 1,
        }
    ).execute()

    yield {
        "step": "device_generated",
        "device_type": device_type,
        "variant_id": variant_id,
        "screenshot_url": persisted["screenshot_url"],
        "html_url": persisted["html_url"],
        "screen_id": device_screen_id,
    }

    yield {
        "step": "ready",
        "screen_id": device_screen_id,
        "device_type": device_type,
    }
