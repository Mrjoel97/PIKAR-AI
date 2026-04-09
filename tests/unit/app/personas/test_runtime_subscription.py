# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for subscription-first persona resolution in resolve_effective_persona.

Priority chain tested:
1. Explicit param / cookie / header wins (short-circuit, no DB call)
2. Active subscription tier overrides profile.persona
3. Profile.persona used when no active subscription
4. Returns None when no subscription and no profile persona
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sub_result(tier: str | None) -> MagicMock:
    """Return a mock Supabase query result with optional subscription data."""
    result = MagicMock()
    if tier is not None:
        result.data = [{"tier": tier}]
    else:
        result.data = []
    return result


# ---------------------------------------------------------------------------
# Test 1: Explicit param / cookie / header short-circuits DB lookups
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explicit_param_wins_no_db_call():
    """When request persona resolves (explicit param/cookie/header), DB is never queried."""
    with patch(
        "app.personas.runtime.resolve_request_persona", return_value="startup"
    ), patch(
        "app.personas.runtime.execute_async",
        new_callable=AsyncMock,
    ) as mock_exec:
        from app.personas.runtime import resolve_effective_persona

        result = await resolve_effective_persona(persona="startup", user_id="user-123")

    assert result == "startup"
    mock_exec.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: Active subscription tier overrides profile.persona
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscription_tier_overrides_profile_persona():
    """With active subscription tier='startup', returns 'startup' even if profile says 'solopreneur'."""
    sub_result = _make_sub_result("startup")

    async def _fake_exec(query_builder, *, timeout=None, op_name=None):
        return sub_result

    mock_onboarding = MagicMock()
    # profile says solopreneur, but subscription says startup
    mock_onboarding.get_user_persona = AsyncMock(return_value="solopreneur")

    with patch(
        "app.personas.runtime.resolve_request_persona", return_value=None
    ), patch(
        "app.personas.runtime.execute_async", new=_fake_exec
    ), patch(
        "app.personas.runtime.get_service_client"
    ) as mock_client, patch(
        "app.services.user_onboarding_service.get_user_onboarding_service",
        return_value=mock_onboarding,
    ):
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value = (
            MagicMock()
        )

        from app.personas.runtime import resolve_effective_persona

        result = await resolve_effective_persona(user_id="user-123")

    # Subscription tier wins; profile is never reached
    assert result == "startup"
    mock_onboarding.get_user_persona.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: Falls back to profile.persona when no active subscription
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_to_profile_persona_when_no_active_subscription():
    """When user has no active subscription (empty rows), falls back to profile.persona."""
    empty_sub_result = _make_sub_result(None)

    async def _fake_exec(query_builder, *, timeout=None, op_name=None):
        return empty_sub_result

    mock_onboarding = MagicMock()
    mock_onboarding.get_user_persona = AsyncMock(return_value="solopreneur")

    with patch(
        "app.personas.runtime.resolve_request_persona", return_value=None
    ), patch(
        "app.personas.runtime.execute_async", new=_fake_exec
    ), patch(
        "app.personas.runtime.get_service_client"
    ) as mock_client, patch(
        "app.services.user_onboarding_service.get_user_onboarding_service",
        return_value=mock_onboarding,
    ):
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value = (
            MagicMock()
        )

        from app.personas.runtime import resolve_effective_persona

        result = await resolve_effective_persona(user_id="user-123")

    assert result == "solopreneur"
    mock_onboarding.get_user_persona.assert_called_once_with("user-123")


# ---------------------------------------------------------------------------
# Test 4: Returns None when no subscription and no profile persona
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_none_when_no_subscription_and_no_profile():
    """When user has no subscription and no profile persona, returns None (unchanged behavior)."""
    empty_sub_result = _make_sub_result(None)

    async def _fake_exec(query_builder, *, timeout=None, op_name=None):
        return empty_sub_result

    mock_onboarding = MagicMock()
    mock_onboarding.get_user_persona = AsyncMock(return_value=None)

    with patch(
        "app.personas.runtime.resolve_request_persona", return_value=None
    ), patch(
        "app.personas.runtime.execute_async", new=_fake_exec
    ), patch(
        "app.personas.runtime.get_service_client"
    ) as mock_client, patch(
        "app.services.user_onboarding_service.get_user_onboarding_service",
        return_value=mock_onboarding,
    ):
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value = (
            MagicMock()
        )

        from app.personas.runtime import resolve_effective_persona

        result = await resolve_effective_persona(user_id="user-123")

    assert result is None
