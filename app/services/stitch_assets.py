# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Stitch Asset Persistence — download Stitch signed URLs, store in Supabase Storage.

Stitch returns short-lived signed URLs for HTML and screenshot files.
This module downloads them immediately within the same tool call and
uploads to the stitch-assets Supabase Storage bucket, returning permanent URLs.
"""

import asyncio
import logging
import mimetypes
from typing import Any

import httpx

from app.services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

BUCKET = "stitch-assets"


async def download_and_persist(
    temp_url: str,
    storage_path: str,
    content_type: str,
) -> str:
    """Download a Stitch temporary URL and store permanently in Supabase Storage.

    Args:
        temp_url: Short-lived signed URL returned by Stitch (expires in minutes).
        storage_path: Destination path inside stitch-assets bucket,
                      e.g. "{user_id}/{project_id}/{screen_id}.html"
        content_type: MIME type, e.g. "text/html" or "image/png".

    Returns:
        Permanent Supabase Storage public URL (string).

    Raises:
        httpx.HTTPStatusError: If the download fails.
    """
    # Download — async httpx handles signed URL redirects transparently
    async with httpx.AsyncClient() as client:
        resp = await client.get(temp_url, follow_redirects=True, timeout=30.0)
        resp.raise_for_status()
        file_bytes = resp.content

    logger.debug(
        "Downloaded %d bytes from Stitch (%s → %s)",
        len(file_bytes),
        content_type,
        storage_path,
    )

    # Upload via sync Supabase client in thread (matches project pattern)
    supabase = get_service_client()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: supabase.storage.from_(BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        ),
    )

    # get_public_url() returns str directly
    public_url: str = supabase.storage.from_(BUCKET).get_public_url(storage_path)
    logger.info("Persisted Stitch asset: %s → %s", storage_path, public_url)
    return public_url


async def persist_screen_assets(
    stitch_response: dict[str, Any],
    user_id: str,
    project_id: str,
    screen_id: str,
    variant_index: int = 0,
) -> dict[str, str | None]:
    """Persist HTML and screenshot assets from a Stitch generate_screen response.

    Extracts html_url and screenshot_url from the Stitch response, downloads
    them, and stores them permanently. Returns a dict with the permanent URLs.

    Args:
        stitch_response: Raw dict from StitchMCPService.call_tool().
        user_id: User UUID (used as storage path prefix for isolation).
        project_id: App project UUID.
        screen_id: Screen UUID.
        variant_index: Variant index (0, 1, 2) for multi-variant generation.

    Returns:
        {"html_url": str | None, "screenshot_url": str | None}
    """
    base_path = f"{user_id}/{project_id}/{screen_id}/v{variant_index}"
    result: dict[str, str | None] = {"html_url": None, "screenshot_url": None}

    html_temp = stitch_response.get("html_url") or stitch_response.get("htmlUrl")
    screenshot_temp = (
        stitch_response.get("screenshot_url") or stitch_response.get("screenshotUrl")
    )

    if html_temp:
        try:
            result["html_url"] = await download_and_persist(
                temp_url=html_temp,
                storage_path=f"{base_path}/screen.html",
                content_type="text/html",
            )
        except Exception as e:
            logger.error("Failed to persist HTML for screen %s: %s", screen_id, e)
            result["html_url"] = html_temp  # fallback to temp URL

    if screenshot_temp:
        # Detect image type from URL extension; default png
        ext = screenshot_temp.split("?")[0].rsplit(".", 1)[-1].lower()
        content_type = mimetypes.types_map.get(f".{ext}", "image/png")
        try:
            result["screenshot_url"] = await download_and_persist(
                temp_url=screenshot_temp,
                storage_path=f"{base_path}/screenshot.{ext}",
                content_type=content_type,
            )
        except Exception as e:
            logger.error(
                "Failed to persist screenshot for screen %s: %s", screen_id, e
            )
            result["screenshot_url"] = screenshot_temp  # fallback to temp URL

    return result
