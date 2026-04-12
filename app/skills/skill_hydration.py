# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Skill hydration from skill_versions table.

On startup, reads all active skill version rows from the DB and patches
the in-memory SkillsRegistry so that refined knowledge survives
Cloud Run cold starts.
"""

import logging

logger = logging.getLogger(__name__)


async def hydrate_skills_from_db() -> int:
    """Read active skill_versions rows and patch registry skills.

    Returns:
        Number of skills hydrated from DB.
    """
    from app.services.supabase_async import execute_async
    from app.services.supabase_client import get_service_client
    from app.skills.registry import skills_registry

    try:
        client = get_service_client()
        resp = await execute_async(
            client.table("skill_versions")
            .select("skill_name, version, knowledge")
            .eq("is_active", True),
            op_name="skill_hydration.fetch_active",
        )
        rows = resp.data or []
    except Exception:
        logger.warning(
            "Skill hydration failed -- using built-in knowledge", exc_info=True
        )
        return 0

    hydrated = 0
    for row in rows:
        skill_name = row.get("skill_name")
        knowledge = row.get("knowledge")
        version = row.get("version")

        if not skill_name or not knowledge:
            continue

        skill = skills_registry.get(skill_name)
        if skill is None:
            logger.debug("Skipping hydration for unknown skill '%s'", skill_name)
            continue

        skill.knowledge = knowledge
        if version:
            skill.version = version
        hydrated += 1

    logger.info("[skill_hydration] Hydrated %d/%d skills from DB", hydrated, len(rows))
    return hydrated
