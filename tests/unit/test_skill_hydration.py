# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for skill hydration from skill_versions DB table."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.skills.registry import Skill, SkillsRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _clean_registry():
    """Provide a clean SkillsRegistry with test skills, restore after test."""
    registry = SkillsRegistry()
    # Stash originals
    original_skills = dict(registry._skills)

    # Register test skills
    registry.register(
        Skill(
            name="test_finance",
            description="Finance skill",
            category="finance",
            version="1.0.0",
            knowledge="Original finance knowledge",
        )
    )
    registry.register(
        Skill(
            name="test_marketing",
            description="Marketing skill",
            category="marketing",
            version="1.0.0",
            knowledge="Original marketing knowledge",
        )
    )

    yield registry

    # Restore
    registry._skills = original_skills


# ---------------------------------------------------------------------------
# hydrate_skills_from_db tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_hydrate_patches_matching_skills(_clean_registry: SkillsRegistry):
    """Skills with an active version row get their knowledge + version updated."""
    mock_resp = MagicMock()
    mock_resp.data = [
        {
            "skill_name": "test_finance",
            "version": "1.1.0",
            "knowledge": "Refined finance knowledge from DB",
        },
    ]

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value = MagicMock()

    with (
        patch(
            "app.skills.skill_hydration.get_service_client",
            return_value=mock_client,
        ),
        patch(
            "app.skills.skill_hydration.execute_async",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ),
    ):
        from app.skills.skill_hydration import hydrate_skills_from_db

        count = await hydrate_skills_from_db()

    assert count == 1
    skill = _clean_registry.get("test_finance")
    assert skill is not None
    assert skill.knowledge == "Refined finance knowledge from DB"
    assert skill.version == "1.1.0"


@pytest.mark.asyncio()
async def test_hydrate_leaves_unmatched_skills_unchanged(
    _clean_registry: SkillsRegistry,
):
    """Skills with no active version row keep their original knowledge."""
    mock_resp = MagicMock()
    mock_resp.data = [
        {
            "skill_name": "test_finance",
            "version": "1.1.0",
            "knowledge": "Refined finance knowledge",
        },
    ]

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value = MagicMock()

    with (
        patch(
            "app.skills.skill_hydration.get_service_client",
            return_value=mock_client,
        ),
        patch(
            "app.skills.skill_hydration.execute_async",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ),
    ):
        from app.skills.skill_hydration import hydrate_skills_from_db

        await hydrate_skills_from_db()

    # Marketing skill was NOT in DB rows -- should be untouched
    marketing = _clean_registry.get("test_marketing")
    assert marketing is not None
    assert marketing.knowledge == "Original marketing knowledge"
    assert marketing.version == "1.0.0"


@pytest.mark.asyncio()
async def test_hydrate_returns_zero_on_db_failure(_clean_registry: SkillsRegistry):
    """DB failure logs a warning and returns 0 without crashing."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value = MagicMock()

    with (
        patch(
            "app.skills.skill_hydration.get_service_client",
            return_value=mock_client,
        ),
        patch(
            "app.skills.skill_hydration.execute_async",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ),
    ):
        from app.skills.skill_hydration import hydrate_skills_from_db

        count = await hydrate_skills_from_db()

    assert count == 0
    # Skills should remain unchanged
    assert _clean_registry.get("test_finance").knowledge == "Original finance knowledge"


@pytest.mark.asyncio()
async def test_hydrate_returns_count_of_hydrated_skills(
    _clean_registry: SkillsRegistry,
):
    """hydrate_skills_from_db returns the count of skills actually hydrated."""
    mock_resp = MagicMock()
    mock_resp.data = [
        {
            "skill_name": "test_finance",
            "version": "2.0.0",
            "knowledge": "New finance",
        },
        {
            "skill_name": "test_marketing",
            "version": "2.0.0",
            "knowledge": "New marketing",
        },
    ]

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value = MagicMock()

    with (
        patch(
            "app.skills.skill_hydration.get_service_client",
            return_value=mock_client,
        ),
        patch(
            "app.skills.skill_hydration.execute_async",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ),
    ):
        from app.skills.skill_hydration import hydrate_skills_from_db

        count = await hydrate_skills_from_db()

    assert count == 2


@pytest.mark.asyncio()
async def test_hydrate_skips_unknown_skills(_clean_registry: SkillsRegistry):
    """Rows for skills not in registry are skipped gracefully."""
    mock_resp = MagicMock()
    mock_resp.data = [
        {
            "skill_name": "nonexistent_skill",
            "version": "1.0.0",
            "knowledge": "Some knowledge",
        },
    ]

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value = MagicMock()

    with (
        patch(
            "app.skills.skill_hydration.get_service_client",
            return_value=mock_client,
        ),
        patch(
            "app.skills.skill_hydration.execute_async",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ),
    ):
        from app.skills.skill_hydration import hydrate_skills_from_db

        count = await hydrate_skills_from_db()

    assert count == 0
