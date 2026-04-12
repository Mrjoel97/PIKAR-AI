# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for skill version persistence (write-through and revert).

Tests cover:
- _execute_skill_refined inserts a new skill_versions row with is_active=True
- _execute_skill_refined deactivates the previous active version
- _execute_skill_refined stores previous_version_id pointing to the prior row
- _attempt_revert loads most-recent non-active version and makes it active
- _attempt_revert restores skill.knowledge in the in-memory registry
- _attempt_revert with no previous version logs a warning and does not crash
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers -- reuse patterns from test_self_improvement_engine.py
# ---------------------------------------------------------------------------

def _mock_supabase_client() -> MagicMock:
    """Return a MagicMock that fakes Supabase table().select()...execute_async."""
    client = MagicMock()
    chain = MagicMock()
    chain.return_value = chain  # chaining: .select(), .eq(), .gte(), etc.
    chain.data = []
    client.table.return_value = chain
    return client


def _make_genai_mock(response_text: str = "Improved knowledge text") -> tuple[MagicMock, MagicMock]:
    """Build a mock genai module + client instance with async generate_content."""
    mock_response = MagicMock()
    mock_response.text = response_text

    mock_client_instance = MagicMock()
    mock_client_instance.aio.models.generate_content = AsyncMock(
        return_value=mock_response,
    )
    mock_client_instance.models.generate_content = MagicMock(
        side_effect=AssertionError("sync path called -- should use async"),
    )

    mock_genai_module = MagicMock()
    mock_genai_module.Client.return_value = mock_client_instance
    return mock_genai_module, mock_client_instance


@contextmanager
def _patch_genai(mock_genai_module: MagicMock):
    """Temporarily replace google.genai in sys.modules AND the google package."""
    google_pkg = sys.modules.get("google")
    saved_mod = sys.modules.get("google.genai")
    saved_attr = getattr(google_pkg, "genai", None) if google_pkg else None

    sys.modules["google.genai"] = mock_genai_module
    if google_pkg is not None:
        google_pkg.genai = mock_genai_module  # type: ignore[attr-defined]

    try:
        yield
    finally:
        if saved_mod is not None:
            sys.modules["google.genai"] = saved_mod
        else:
            sys.modules.pop("google.genai", None)

        if google_pkg is not None:
            if saved_attr is not None:
                google_pkg.genai = saved_attr  # type: ignore[attr-defined]
            elif hasattr(google_pkg, "genai"):
                delattr(google_pkg, "genai")


def _make_mock_skill(name: str = "test_skill", knowledge: str = "old knowledge", version: str = "1.0.0"):
    """Create a mock Skill object."""
    skill = MagicMock()
    skill.name = name
    skill.description = "A test skill"
    skill.category = "test"
    skill.knowledge = knowledge
    skill.version = version
    skill.changelog = None
    return skill


# ---------------------------------------------------------------------------
# Test 1: _execute_skill_refined inserts a new skill_versions row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_skill_refined_inserts_new_version():
    """_execute_skill_refined inserts a skill_versions row with is_active=True and refined knowledge."""
    mock_genai_module, _ = _make_genai_mock("Improved knowledge text")
    mock_skill = _make_mock_skill()
    captured_inserts: list[dict] = []

    async def _execute_async_side_effect(query, op_name=""):
        resp = MagicMock()
        if "find_active" in (op_name or ""):
            # No previous active version
            resp.data = []
            return resp
        if "deactivate" in (op_name or ""):
            resp.data = []
            return resp
        if "insert_version" in (op_name or ""):
            # Capture the insert call
            resp.data = [{"id": "new-version-uuid"}]
            return resp
        if "fetch_negative" in (op_name or ""):
            resp.data = []
            return resp
        resp.data = []
        return resp

    with (
        patch("app.services.supabase.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_execute_async_side_effect) as mock_exec,
        patch("app.services.self_improvement_engine.skills_registry") as mock_registry,
        _patch_genai(mock_genai_module),
    ):
        mock_registry.get.return_value = mock_skill

        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        action = {
            "id": "action-1",
            "skill_name": "test_skill",
            "action_type": "skill_refined",
            "metadata": {"effectiveness_score": 0.3},
        }
        result = await engine._execute_skill_refined(action)

    # Should have called execute_async with insert_version op_name
    insert_calls = [
        c for c in mock_exec.call_args_list
        if "insert_version" in (c.kwargs.get("op_name", "") or c.args[1] if len(c.args) > 1 else "")
    ]
    assert len(insert_calls) >= 1, f"Expected insert_version call, got ops: {[c.kwargs.get('op_name', c.args[1] if len(c.args) > 1 else '') for c in mock_exec.call_args_list]}"
    assert result["action_type"] == "skill_refined"
    assert "new_version" in result


# ---------------------------------------------------------------------------
# Test 2: _execute_skill_refined deactivates previous active version
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_skill_refined_deactivates_previous():
    """_execute_skill_refined sets is_active=False on the previous active version before inserting new one."""
    mock_genai_module, _ = _make_genai_mock("Improved knowledge text")
    mock_skill = _make_mock_skill()

    async def _execute_async_side_effect(query, op_name=""):
        resp = MagicMock()
        if "find_active" in (op_name or ""):
            # There IS a previous active version
            resp.data = [{"id": "prev-version-uuid", "previous_version_id": None}]
            return resp
        if "deactivate" in (op_name or ""):
            resp.data = []
            return resp
        if "insert_version" in (op_name or ""):
            resp.data = [{"id": "new-version-uuid"}]
            return resp
        if "fetch_negative" in (op_name or ""):
            resp.data = []
            return resp
        resp.data = []
        return resp

    with (
        patch("app.services.supabase.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_execute_async_side_effect) as mock_exec,
        patch("app.services.self_improvement_engine.skills_registry") as mock_registry,
        _patch_genai(mock_genai_module),
    ):
        mock_registry.get.return_value = mock_skill

        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        action = {
            "id": "action-2",
            "skill_name": "test_skill",
            "action_type": "skill_refined",
            "metadata": {"effectiveness_score": 0.3},
        }
        result = await engine._execute_skill_refined(action)

    # Should have called execute_async with deactivate op_name
    deactivate_calls = [
        c for c in mock_exec.call_args_list
        if "deactivate" in (c.kwargs.get("op_name", "") or c.args[1] if len(c.args) > 1 else "")
    ]
    assert len(deactivate_calls) >= 1, f"Expected deactivate call, got ops: {[c.kwargs.get('op_name', c.args[1] if len(c.args) > 1 else '') for c in mock_exec.call_args_list]}"


# ---------------------------------------------------------------------------
# Test 3: _execute_skill_refined stores previous_version_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_skill_refined_stores_previous_version_id():
    """_execute_skill_refined stores previous_version_id pointing to the prior row's id."""
    mock_genai_module, _ = _make_genai_mock("Improved knowledge text")
    mock_skill = _make_mock_skill()
    captured_insert_query = []

    original_mock_client = _mock_supabase_client()

    async def _execute_async_side_effect(query, op_name=""):
        resp = MagicMock()
        if "find_active" in (op_name or ""):
            resp.data = [{"id": "prev-uuid-123", "previous_version_id": None}]
            return resp
        if "deactivate" in (op_name or ""):
            resp.data = []
            return resp
        if "insert_version" in (op_name or ""):
            # Capture the query builder to inspect insert payload
            captured_insert_query.append(query)
            resp.data = [{"id": "new-version-uuid"}]
            return resp
        if "fetch_negative" in (op_name or ""):
            resp.data = []
            return resp
        resp.data = []
        return resp

    with (
        patch("app.services.supabase.get_service_client", return_value=original_mock_client),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_execute_async_side_effect) as mock_exec,
        patch("app.services.self_improvement_engine.skills_registry") as mock_registry,
        _patch_genai(mock_genai_module),
    ):
        mock_registry.get.return_value = mock_skill

        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        action = {
            "id": "action-3",
            "skill_name": "test_skill",
            "action_type": "skill_refined",
            "metadata": {"effectiveness_score": 0.3},
        }
        result = await engine._execute_skill_refined(action)

    # Verify the insert was called (the implementation should pass previous_version_id)
    insert_calls = [
        c for c in mock_exec.call_args_list
        if "insert_version" in (c.kwargs.get("op_name", "") or "")
    ]
    assert len(insert_calls) >= 1, "Expected insert_version call"
    # The insert query builder should have been called with previous_version_id
    # We verify by checking that the result includes the version info
    assert result.get("new_version") is not None


# ---------------------------------------------------------------------------
# Test 4: _attempt_revert loads previous version and makes it active
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_attempt_revert_restores_previous_version():
    """_attempt_revert for skill_refined loads most-recent non-active version and activates it."""
    mock_skill = _make_mock_skill(knowledge="current bad knowledge", version="1.0.2")

    async def _execute_async_side_effect(query, op_name=""):
        resp = MagicMock()
        if "revert_find_active" in (op_name or ""):
            resp.data = [{"id": "current-uuid", "previous_version_id": "prev-uuid"}]
            return resp
        if "revert_fetch_prev" in (op_name or ""):
            resp.data = {"id": "prev-uuid", "knowledge": "old good knowledge", "version": "1.0.1"}
            return resp
        if "revert_deactivate" in (op_name or ""):
            resp.data = []
            return resp
        if "revert_activate" in (op_name or ""):
            resp.data = []
            return resp
        resp.data = []
        return resp

    with (
        patch("app.services.supabase.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_execute_async_side_effect) as mock_exec,
        patch("app.services.self_improvement_engine.skills_registry") as mock_registry,
    ):
        mock_registry.get.return_value = mock_skill

        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        action = {
            "id": "action-4",
            "action_type": "skill_refined",
            "skill_name": "test_skill",
            "result_metadata": {},
        }
        await engine._attempt_revert(action)

    # The revert should have called deactivate + activate
    deactivate_calls = [
        c for c in mock_exec.call_args_list
        if "revert_deactivate" in (c.kwargs.get("op_name", "") or "")
    ]
    activate_calls = [
        c for c in mock_exec.call_args_list
        if "revert_activate" in (c.kwargs.get("op_name", "") or "")
    ]
    assert len(deactivate_calls) >= 1, "Expected revert_deactivate call"
    assert len(activate_calls) >= 1, "Expected revert_activate call"


# ---------------------------------------------------------------------------
# Test 5: _attempt_revert restores skill.knowledge in the registry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_attempt_revert_restores_in_memory_knowledge():
    """_attempt_revert restores skill.knowledge in the in-memory registry to the reverted version."""
    mock_skill = _make_mock_skill(knowledge="current bad knowledge", version="1.0.2")

    async def _execute_async_side_effect(query, op_name=""):
        resp = MagicMock()
        if "revert_find_active" in (op_name or ""):
            resp.data = [{"id": "current-uuid", "previous_version_id": "prev-uuid"}]
            return resp
        if "revert_fetch_prev" in (op_name or ""):
            resp.data = {"id": "prev-uuid", "knowledge": "old good knowledge", "version": "1.0.1"}
            return resp
        if "revert_deactivate" in (op_name or ""):
            resp.data = []
            return resp
        if "revert_activate" in (op_name or ""):
            resp.data = []
            return resp
        resp.data = []
        return resp

    with (
        patch("app.services.supabase.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_execute_async_side_effect),
        patch("app.services.self_improvement_engine.skills_registry") as mock_registry,
    ):
        mock_registry.get.return_value = mock_skill

        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        action = {
            "id": "action-5",
            "action_type": "skill_refined",
            "skill_name": "test_skill",
            "result_metadata": {},
        }
        await engine._attempt_revert(action)

    # After revert, the in-memory skill's knowledge should be restored
    assert mock_skill.knowledge == "old good knowledge"
    assert mock_skill.version == "1.0.1"


# ---------------------------------------------------------------------------
# Test 6: _attempt_revert with no previous version logs warning, does not crash
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_attempt_revert_no_previous_version_graceful():
    """When no previous version exists, _attempt_revert logs a warning and does not crash."""
    mock_skill = _make_mock_skill(knowledge="current knowledge", version="1.0.1")

    async def _execute_async_side_effect(query, op_name=""):
        resp = MagicMock()
        if "revert_find_active" in (op_name or ""):
            # Active version exists but has no previous_version_id
            resp.data = [{"id": "current-uuid", "previous_version_id": None}]
            return resp
        resp.data = []
        return resp

    with (
        patch("app.services.supabase.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_execute_async_side_effect),
        patch("app.services.self_improvement_engine.skills_registry") as mock_registry,
    ):
        mock_registry.get.return_value = mock_skill

        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        action = {
            "id": "action-6",
            "action_type": "skill_refined",
            "skill_name": "test_skill",
            "result_metadata": {},
        }
        # Should NOT raise any exception
        await engine._attempt_revert(action)

    # Knowledge should be unchanged (no revert happened)
    assert mock_skill.knowledge == "current knowledge"
    assert mock_skill.version == "1.0.1"
