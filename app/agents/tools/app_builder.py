# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""App Builder agent tools — ADK-compatible async wrappers for Stitch MCP.

These functions are added to agent tool lists directly.
They delegate to StitchMCPService (the persistent singleton) via direct await.
"""

import logging
from typing import Any

from app.services.prompt_enhancer import enhance_prompt
from app.services.stitch_assets import persist_screen_assets

logger = logging.getLogger(__name__)


async def _generate_screen_async(
    prompt: str,
    project_id: str,
    device_type: str = "DESKTOP",
    enhance: bool = True,
    user_id: str | None = None,
    project_uuid: str | None = None,
    screen_id: str | None = None,
    variant_index: int = 0,
) -> dict[str, Any]:
    """Async inner for generate_app_screen."""
    from app.services.stitch_mcp import get_stitch_service

    service = await get_stitch_service(user_id)

    # Step 1: Optionally enhance the prompt with Gemini Flash
    final_prompt = prompt
    if enhance:
        final_prompt = await enhance_prompt(prompt)

    # Step 2: Call Stitch to generate the screen
    stitch_result = await service.call_tool(
        "generate_screen_from_text",
        {"prompt": final_prompt, "projectId": project_id, "deviceType": device_type},
    )

    # Step 3: Persist assets if we have the required IDs
    if user_id and project_uuid and screen_id:
        persisted = await persist_screen_assets(
            stitch_response=stitch_result,
            user_id=user_id,
            project_id=project_uuid,
            screen_id=screen_id,
            variant_index=variant_index,
        )
        stitch_result.update(persisted)

    stitch_result["enhanced_prompt"] = final_prompt
    return stitch_result


async def generate_app_screen(
    prompt: str,
    project_id: str,
    device_type: str = "DESKTOP",
    enhance: bool = True,
    user_id: str | None = None,
    project_uuid: str | None = None,
    screen_id: str | None = None,
    variant_index: int = 0,
) -> dict[str, Any]:
    """Generate a screen via Stitch MCP for the given project.

    Args:
        prompt: Description of the screen to generate (enhanced by default).
        project_id: The Stitch project ID to generate within.
        device_type: "DESKTOP", "MOBILE", or "TABLET".
        enhance: If True, expand the prompt with Gemini Flash before calling Stitch.
        user_id: User UUID for asset storage path isolation (optional).
        project_uuid: App project UUID for asset storage (optional).
        screen_id: Screen UUID for asset storage (optional).
        variant_index: Variant index (0, 1, 2) for multi-variant generation.

    Returns:
        Parsed JSON response from Stitch containing screenId, asset URLs,
        and enhanced_prompt used for generation.
    """
    try:
        return await _generate_screen_async(
            prompt=prompt,
            project_id=project_id,
            device_type=device_type,
            enhance=enhance,
            user_id=user_id,
            project_uuid=project_uuid,
            screen_id=screen_id,
            variant_index=variant_index,
        )
    except RuntimeError as e:
        logger.error("generate_app_screen failed: %s", e)
        return {"success": False, "error": str(e)}


async def _list_stitch_tools_async(user_id: str | None = None) -> dict[str, Any]:
    """List tools exposed by the running Stitch MCP server."""
    from app.services.stitch_mcp import get_stitch_service

    service = await get_stitch_service(user_id)
    # Piggyback on call_tool's lock pattern; use list_tools directly on session
    async with service._lock:
        tools_result = await service._session.list_tools()
    return {
        "tools": [
            {"name": t.name, "description": t.description} for t in tools_result.tools
        ]
    }


async def list_stitch_tools(user_id: str | None = None) -> dict[str, Any]:
    """List all tools available from the connected Stitch MCP server.

    Args:
        user_id: User UUID; routes to the user's Stitch subprocess if a
            per-user key is configured. Falls back to the env-default pool.

    Returns:
        Dict with 'tools' list of {name, description}.
    """
    try:
        return await _list_stitch_tools_async(user_id=user_id)
    except RuntimeError as e:
        return {"success": False, "error": str(e), "tools": []}


async def _enhance_description_async(
    description: str,
    domain_hint: str | None = None,
) -> dict[str, Any]:
    """Async inner for enhance_description."""
    enhanced = await enhance_prompt(description, domain_hint)
    return {"enhanced": enhanced, "original": description}


async def enhance_description(
    description: str,
    domain_hint: str | None = None,
) -> dict[str, Any]:
    """Expand a vague app description into a Stitch-optimized specification.

    Args:
        description: Vague user input, e.g. "bakery website".
        domain_hint: Optional domain category (bakery, saas, restaurant, fitness).

    Returns:
        Dict with 'enhanced' (structured spec) and 'original' keys.
    """
    try:
        return await _enhance_description_async(description, domain_hint)
    except Exception as e:
        logger.error("enhance_description failed: %s", e)
        return {"enhanced": description, "original": description, "error": str(e)}


APP_BUILDER_TOOLS = [generate_app_screen, list_stitch_tools, enhance_description]
