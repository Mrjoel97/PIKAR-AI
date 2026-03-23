"""Ship stage orchestrator — generate all selected output targets and stream SSE events.

Sequentially produces each selected output target (react, pwa, capacitor, video),
uploads results to stitch-assets bucket, and yields SSE progress events.
Sequential (not concurrent) per RESEARCH.md — Remotion subprocess is CPU-intensive.
"""

import asyncio
import io
import logging
import zipfile
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.services.capacitor_generator import generate_capacitor_zip
from app.services.pwa_generator import generate_pwa_zip
from app.services.react_converter import convert_html_to_react_zip
from app.services.remotion_render_service import render_scenes_direct_to_mp4
from app.services.stitch_assets import BUCKET
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Walkthrough scene builder
# ---------------------------------------------------------------------------


def _build_walkthrough_scenes(screens: list[dict], project_title: str) -> list[dict]:
    """Build a Remotion scene list for a walkthrough video.

    Produces: intro scene (project title, 3s), one scene per screen (4s each,
    with screenshot imageUrl and fade transition), and an outro scene (2s).

    Args:
        screens: List of screen dicts with at minimum ``name`` and ``screenshot_url``.
        project_title: App project title shown in the intro scene.

    Returns:
        Ordered list of scene dicts ready for render_scenes_direct_to_mp4.
    """
    scenes: list[dict] = []

    # Intro
    scenes.append({"text": project_title, "duration": 3})

    # One scene per approved screen
    for screen in screens:
        scenes.append(
            {
                "text": screen.get("name", "Screen"),
                "duration": 4,
                "imageUrl": screen.get("screenshot_url") or None,
                "transition": {"type": "fade", "durationFrames": 15},
            }
        )

    # Outro
    scenes.append({"text": "Built with Pikar AI", "duration": 2})

    return scenes


# ---------------------------------------------------------------------------
# Upload helper
# ---------------------------------------------------------------------------


async def _upload_output_bytes(
    file_bytes: bytes,
    storage_path: str,
    content_type: str,
) -> str:
    """Upload in-memory bytes to stitch-assets bucket and return the public URL.

    Args:
        file_bytes: Raw bytes to upload.
        storage_path: Destination path inside stitch-assets bucket.
        content_type: MIME type, e.g. ``application/zip`` or ``video/mp4``.

    Returns:
        Permanent Supabase Storage public URL.
    """
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
    public_url: str = supabase.storage.from_(BUCKET).get_public_url(storage_path)
    logger.info("Uploaded ship output: %s (%d bytes)", storage_path, len(file_bytes))
    return public_url


# ---------------------------------------------------------------------------
# DB fetch helper
# ---------------------------------------------------------------------------


async def _fetch_approved_screens(
    project_id: str, user_id: str
) -> tuple[list[dict], dict]:
    """Fetch approved screens with their selected variant URLs and project data.

    Queries app_screens where ``approved = true``, then fetches screen_variants
    where ``is_selected = true`` to get html_url and screenshot_url. Also fetches
    app_projects for title and design_system.

    Args:
        project_id: App project UUID.
        user_id: User UUID for ownership scoping.

    Returns:
        Tuple of (screens_with_urls, project_data) where screens_with_urls is a
        list of dicts combining screen fields with html_url and screenshot_url.
    """
    supabase = get_service_client()

    # Fetch project metadata
    proj_result = (
        supabase.table("app_projects")
        .select("title, design_system")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    project_data: dict = proj_result.data or {}

    # Fetch approved screens
    screens_result = (
        supabase.table("app_screens")
        .select("id, name, user_id")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .eq("approved", True)
        .execute()
    )
    screens: list[dict] = screens_result.data or []
    if not screens:
        return [], project_data

    screen_ids = [s["id"] for s in screens]

    # Fetch selected variants for approved screens
    variants_result = (
        supabase.table("screen_variants")
        .select("screen_id, html_url, screenshot_url")
        .eq("is_selected", True)
        .execute()
    )
    all_selected: list[dict] = variants_result.data or []

    # Build lookup: screen_id -> variant URLs
    url_map: dict[str, dict] = {
        v["screen_id"]: {
            "html_url": v.get("html_url") or "",
            "screenshot_url": v.get("screenshot_url") or "",
        }
        for v in all_selected
        if v.get("screen_id") in screen_ids
    }

    screens_with_urls = [
        {
            "id": s["id"],
            "name": s["name"],
            "html_url": url_map.get(s["id"], {}).get("html_url", ""),
            "screenshot_url": url_map.get(s["id"], {}).get("screenshot_url", ""),
        }
        for s in screens
    ]

    return screens_with_urls, project_data


# ---------------------------------------------------------------------------
# Per-target ship helpers
# ---------------------------------------------------------------------------


async def _ship_react(
    project_id: str,
    user_id: str,
    screens: list[dict],
    design_system: dict | None,
) -> str:
    """Convert all approved screens to React/TS and produce one master ZIP.

    For each screen, downloads HTML via httpx and calls convert_html_to_react_zip.
    Then merges all per-screen ZIPs into a single master ZIP, placing each screen's
    files under a ``{screen_name}/`` subdirectory prefix to prevent collisions.

    Args:
        project_id: App project UUID (used for storage path).
        user_id: User UUID (used for storage path).
        screens: List of screen dicts with html_url and name.
        design_system: Optional design system dict for React conversion context.

    Returns:
        Public URL of the uploaded master ZIP.
    """
    master_buf = io.BytesIO()
    master_zip = zipfile.ZipFile(master_buf, "w", compression=zipfile.ZIP_DEFLATED)

    async with httpx.AsyncClient() as client:
        for screen in screens:
            html_url = screen.get("html_url") or ""
            screen_name = screen.get("name") or "Screen"

            if html_url:
                resp = await client.get(html_url, follow_redirects=True, timeout=30.0)
                resp.raise_for_status()
                html_content = resp.text
            else:
                html_content = "<html><body></body></html>"

            screen_zip_bytes = await convert_html_to_react_zip(
                html_content=html_content,
                screen_name=screen_name,
                design_system=design_system,
            )

            # Merge per-screen ZIP into master under subdirectory
            screen_zip = zipfile.ZipFile(io.BytesIO(screen_zip_bytes))
            safe_name = screen_name.replace("/", "_").replace("\\", "_")
            for entry in screen_zip.namelist():
                entry_bytes = screen_zip.read(entry)
                master_zip.writestr(f"{safe_name}/{entry}", entry_bytes)
            screen_zip.close()

    master_zip.close()
    master_bytes = master_buf.getvalue()

    storage_path = f"{user_id}/{project_id}/ship/react-components.zip"
    return await _upload_output_bytes(master_bytes, storage_path, "application/zip")


async def _ship_pwa(
    project_id: str,
    user_id: str,
    screens: list[dict],
    design_system: dict | None,
    app_name: str,
) -> str:
    """Combine all screen HTML and generate a PWA ZIP.

    Args:
        project_id: App project UUID.
        user_id: User UUID.
        screens: List of screen dicts with html_url.
        design_system: Optional design system dict.
        app_name: Human-readable app name for the PWA manifest.

    Returns:
        Public URL of the uploaded PWA ZIP.
    """
    combined_html = "\n".join(
        s.get("html_url") or "" for s in screens if s.get("html_url")
    )
    pwa_bytes = await generate_pwa_zip(
        app_name=app_name,
        html_content=combined_html,
        design_system=design_system,
    )
    storage_path = f"{user_id}/{project_id}/ship/pwa.zip"
    return await _upload_output_bytes(pwa_bytes, storage_path, "application/zip")


async def _ship_capacitor(
    project_id: str,
    user_id: str,
    screens: list[dict],
    app_name: str,
) -> str:
    """Combine all screen HTML and generate a Capacitor scaffold ZIP.

    Args:
        project_id: App project UUID.
        user_id: User UUID.
        screens: List of screen dicts with html_url.
        app_name: Human-readable app name for the Capacitor project.

    Returns:
        Public URL of the uploaded Capacitor ZIP.
    """
    combined_html = "\n".join(
        s.get("html_url") or "" for s in screens if s.get("html_url")
    )
    cap_bytes = await generate_capacitor_zip(
        app_name=app_name,
        html_content=combined_html,
    )
    storage_path = f"{user_id}/{project_id}/ship/capacitor.zip"
    return await _upload_output_bytes(cap_bytes, storage_path, "application/zip")


async def _ship_video(
    project_id: str,
    user_id: str,
    screens: list[dict],
    project_title: str,
) -> str:
    """Generate a Remotion walkthrough video from approved screen screenshots.

    Builds a scene list via _build_walkthrough_scenes, then calls
    render_scenes_direct_to_mp4 via asyncio.to_thread (non-blocking).
    Uploads the resulting MP4 to stitch-assets.

    Args:
        project_id: App project UUID.
        user_id: User UUID.
        screens: List of screen dicts with name and screenshot_url.
        project_title: Project title used in the intro scene.

    Returns:
        Public URL of the uploaded MP4.

    Raises:
        RuntimeError: If Remotion render is disabled or the render failed.
    """
    scenes = _build_walkthrough_scenes(screens, project_title)
    total_duration = sum(scene["duration"] for scene in scenes)

    mp4_bytes, _asset_id = await asyncio.to_thread(
        render_scenes_direct_to_mp4,
        scenes,
        total_duration,
        user_id,
    )

    if mp4_bytes is None:
        raise RuntimeError("Remotion render disabled or failed")

    storage_path = f"{user_id}/{project_id}/ship/walkthrough.mp4"
    return await _upload_output_bytes(mp4_bytes, storage_path, "video/mp4")


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


async def ship_project(
    project_id: str,
    user_id: str,
    targets: list[str],
) -> AsyncIterator[dict[str, Any]]:
    """Orchestrate the ship stage: generate all selected output targets via SSE events.

    Fetches approved screens and project data, then for each target in ``targets``
    sequentially: yields ``target_started``, calls the corresponding ``_ship_*``
    function, yields ``target_complete`` (with URL) or ``target_failed`` (with error).
    After all targets: yields ``ship_complete`` with a downloads dict and updates
    app_projects stage to "done" and status to "exported".

    Targets are processed SEQUENTIALLY (not asyncio.gather) — Remotion subprocess
    is CPU-intensive and cannot safely run concurrently.

    Args:
        project_id: App project UUID.
        user_id: User UUID.
        targets: Ordered list of targets to generate (``react``, ``pwa``, ``capacitor``, ``video``).

    Yields:
        SSE event dicts with ``step`` field and target-specific payload.
    """
    screens, project_data = await _fetch_approved_screens(project_id, user_id)
    app_name: str = project_data.get("title") or "My App"
    design_system: dict | None = project_data.get("design_system") or None

    downloads: dict[str, str] = {}

    for target in targets:
        yield {"step": "target_started", "target": target}

        try:
            if target == "react":
                url = await _ship_react(project_id, user_id, screens, design_system)
            elif target == "pwa":
                url = await _ship_pwa(
                    project_id, user_id, screens, design_system, app_name
                )
            elif target == "capacitor":
                url = await _ship_capacitor(project_id, user_id, screens, app_name)
            elif target == "video":
                url = await _ship_video(project_id, user_id, screens, app_name)
            else:
                raise ValueError(f"Unknown target: {target!r}")

            downloads[target] = url
            yield {"step": "target_complete", "target": target, "url": url}

        except Exception as exc:
            logger.warning("Ship target %r failed: %s", target, exc)
            yield {"step": "target_failed", "target": target, "error": str(exc)}

    yield {"step": "ship_complete", "downloads": downloads}

    # Advance project stage
    supabase = get_service_client()
    supabase.table("app_projects").update(
        {"stage": "done", "status": "exported"}
    ).eq("id", project_id).eq("user_id", user_id).execute()
