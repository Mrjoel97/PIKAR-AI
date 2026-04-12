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

# Patch targets: lazy imports inside hydrate_skills_from_db resolve at call time,
# so we patch the source modules rather than the hydration module namespace.
_PATCH_CLIENT = "app.services.supabase_client.get_service_client"
_PATCH_EXEC = "app.services.supabase_async.execute_async"


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
        patch(_PATCH_CLIENT, return_value=mock_client),
        patch(_PATCH_EXEC, new_callable=AsyncMock, return_value=mock_resp),
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
        patch(_PATCH_CLIENT, return_value=mock_client),
        patch(_PATCH_EXEC, new_callable=AsyncMock, return_value=mock_resp),
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
        patch(_PATCH_CLIENT, return_value=mock_client),
        patch(_PATCH_EXEC, new_callable=AsyncMock, side_effect=Exception("Connection refused")),
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
        patch(_PATCH_CLIENT, return_value=mock_client),
        patch(_PATCH_EXEC, new_callable=AsyncMock, return_value=mock_resp),
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
        patch(_PATCH_CLIENT, return_value=mock_client),
        patch(_PATCH_EXEC, new_callable=AsyncMock, return_value=mock_resp),
    ):
        from app.skills.skill_hydration import hydrate_skills_from_db

        count = await hydrate_skills_from_db()

    assert count == 0


# ---------------------------------------------------------------------------
# Skill version history endpoint tests
# ---------------------------------------------------------------------------

# The endpoint is on the self_improvement router. We test the handler function
# directly with mocked DB responses to avoid heavy TestClient setup.
_PATCH_HISTORY_CLIENT = "app.routers.self_improvement.get_service_client"
_PATCH_HISTORY_EXEC = "app.routers.self_improvement.execute_async"


def _make_version_row(
    *,
    skill_name: str = "seo_checklist",
    version: str = "1.0.0",
    knowledge: str = "Some knowledge text",
    vid: str = "v-001",
    prev_id: str | None = None,
    source_action_id: str | None = None,
    created_by: str = "system:self-improvement-engine",
    created_at: str = "2026-04-12T10:00:00Z",
    is_active: bool = False,
) -> dict:
    """Build a skill_versions row dict for test fixtures."""
    return {
        "id": vid,
        "skill_name": skill_name,
        "version": version,
        "knowledge": knowledge,
        "previous_version_id": prev_id,
        "source_action_id": source_action_id,
        "created_by": created_by,
        "created_at": created_at,
        "is_active": is_active,
        "metadata": {},
    }


@pytest.mark.asyncio()
async def test_history_returns_ordered_versions_newest_first():
    """GET /self-improvement/skills/{name}/history returns newest-first chain."""
    rows = [
        _make_version_row(
            vid="v-002",
            version="1.1.0",
            knowledge="Expanded knowledge with more detail",
            prev_id="v-001",
            created_at="2026-04-12T12:00:00Z",
            is_active=True,
        ),
        _make_version_row(
            vid="v-001",
            version="1.0.0",
            knowledge="Initial knowledge",
            created_at="2026-04-12T10:00:00Z",
        ),
    ]
    mock_resp = MagicMock()
    mock_resp.data = rows

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value = (
        MagicMock()
    )

    with (
        patch(_PATCH_HISTORY_CLIENT, return_value=mock_client),
        patch(_PATCH_HISTORY_EXEC, new_callable=AsyncMock, return_value=mock_resp),
    ):
        from app.routers.self_improvement import get_skill_version_history

        result = await get_skill_version_history(
            request=MagicMock(),
            name="seo_checklist",
            _current_user_id="test-user",
        )

    assert result["total"] == 2
    versions = result["versions"]
    assert versions[0]["version"] == "1.1.0"
    assert versions[1]["version"] == "1.0.0"


@pytest.mark.asyncio()
async def test_history_includes_diff_summary():
    """Each version has a diff_summary describing what changed from previous."""
    rows = [
        _make_version_row(
            vid="v-002",
            version="1.1.0",
            knowledge="A" * 1200,
            prev_id="v-001",
            created_at="2026-04-12T12:00:00Z",
            is_active=True,
        ),
        _make_version_row(
            vid="v-001",
            version="1.0.0",
            knowledge="A" * 450,
            created_at="2026-04-12T10:00:00Z",
        ),
    ]
    mock_resp = MagicMock()
    mock_resp.data = rows

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value = (
        MagicMock()
    )

    with (
        patch(_PATCH_HISTORY_CLIENT, return_value=mock_client),
        patch(_PATCH_HISTORY_EXEC, new_callable=AsyncMock, return_value=mock_resp),
    ):
        from app.routers.self_improvement import get_skill_version_history

        result = await get_skill_version_history(
            request=MagicMock(),
            name="seo_checklist",
            _current_user_id="test-user",
        )

    versions = result["versions"]
    # v-002 has a previous version => diff summary references length change
    assert "450" in versions[0]["diff_summary"]
    assert "1200" in versions[0]["diff_summary"]
    # v-001 is the initial version
    assert versions[1]["diff_summary"] == "Initial version"


@pytest.mark.asyncio()
async def test_history_empty_returns_200_with_empty_list():
    """When no versions exist for a skill, returns empty list (not 404)."""
    mock_resp = MagicMock()
    mock_resp.data = []

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value = (
        MagicMock()
    )

    with (
        patch(_PATCH_HISTORY_CLIENT, return_value=mock_client),
        patch(_PATCH_HISTORY_EXEC, new_callable=AsyncMock, return_value=mock_resp),
    ):
        from app.routers.self_improvement import get_skill_version_history

        result = await get_skill_version_history(
            request=MagicMock(),
            name="nonexistent_skill",
            _current_user_id="test-user",
        )

    assert result["versions"] == []
    assert result["total"] == 0
    assert result["skill_name"] == "nonexistent_skill"


@pytest.mark.asyncio()
async def test_history_initial_version_says_initial():
    """The first version (no previous_version_id) says 'Initial version'."""
    rows = [
        _make_version_row(
            vid="v-001",
            version="1.0.0",
            knowledge="First knowledge",
            prev_id=None,
            created_at="2026-04-12T10:00:00Z",
            is_active=True,
        ),
    ]
    mock_resp = MagicMock()
    mock_resp.data = rows

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value = (
        MagicMock()
    )

    with (
        patch(_PATCH_HISTORY_CLIENT, return_value=mock_client),
        patch(_PATCH_HISTORY_EXEC, new_callable=AsyncMock, return_value=mock_resp),
    ):
        from app.routers.self_improvement import get_skill_version_history

        result = await get_skill_version_history(
            request=MagicMock(),
            name="seo_checklist",
            _current_user_id="test-user",
        )

    assert result["total"] == 1
    assert result["versions"][0]["diff_summary"] == "Initial version"
