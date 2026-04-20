from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.user_onboarding_service import UserOnboardingService


@pytest.fixture
def onboarding_service(monkeypatch: pytest.MonkeyPatch) -> tuple[
    UserOnboardingService,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    mock_supabase = MagicMock()
    mock_agent_factory = MagicMock()
    mock_cache = MagicMock()
    mock_cache.invalidate_user_all = AsyncMock()

    monkeypatch.setattr(
        "app.services.user_onboarding_service.get_service_client",
        lambda: mock_supabase,
    )
    monkeypatch.setattr(
        "app.services.user_onboarding_service.get_user_agent_factory",
        lambda: mock_agent_factory,
    )
    monkeypatch.setattr(
        "app.services.user_onboarding_service.get_cache_service",
        lambda: mock_cache,
    )

    return UserOnboardingService(), mock_supabase, mock_agent_factory, mock_cache


def test_build_onboarding_brief_markdown_includes_saved_context(
    onboarding_service: tuple[UserOnboardingService, MagicMock, MagicMock, MagicMock],
) -> None:
    service, _, _, _ = onboarding_service

    markdown = service._build_onboarding_brief_markdown(
        business_context={
            "company_name": "Acme Studio",
            "industry": "Technology / SaaS",
            "team_size": "solo",
            "role": "Founder",
            "website": "https://acme.example",
            "description": "An AI studio for small businesses.",
            "goals": ["growth", "automation"],
        },
        preferences={
            "tone": "supportive",
            "verbosity": "balanced",
            "communication_style": "direct",
            "notification_frequency": "daily",
        },
        persona="solopreneur",
        agent_name="Ava",
        agent_setup={"focus_areas": ["sales", "content"]},
    )

    assert "# Acme Studio Onboarding Brief" in markdown
    assert "- Chosen agent name: Ava" in markdown
    assert "- Tone: supportive" in markdown
    assert "- growth" in markdown
    assert "Do not ask the user to repeat" not in markdown
    assert "Start from this saved business context" in markdown


@pytest.mark.asyncio
async def test_complete_onboarding_syncs_onboarding_brief_with_full_context(
    onboarding_service: tuple[UserOnboardingService, MagicMock, MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _, mock_agent_factory, mock_cache = onboarding_service

    profile_data = {
        "business_context": {
            "company_name": "Acme Studio",
            "industry": "Technology / SaaS",
            "description": "An AI studio for small businesses.",
            "goals": ["growth"],
        },
        "persona": "solopreneur",
        "preferences": {
            "tone": "supportive",
            "verbosity": "balanced",
            "communication_style": "direct",
            "notification_frequency": "daily",
        },
    }
    agent_data = {
        "agent_name": "Ava",
        "configuration": {
            "agent_setup": {
                "focus_areas": ["sales", "content"],
            }
        },
    }

    responses = iter(
        [
            SimpleNamespace(data=profile_data),
            SimpleNamespace(data=agent_data),
            SimpleNamespace(data=[{"user_id": "user-123"}]),
        ]
    )

    async def fake_execute_async(*args, **kwargs):
        return next(responses)

    sync_mock = AsyncMock()
    schedule_mock = AsyncMock()
    monkeypatch.setattr(
        "app.services.user_onboarding_service.execute_async",
        fake_execute_async,
    )
    service._sync_onboarding_brief_to_vault = sync_mock
    service._schedule_post_onboarding = schedule_mock

    result = await service.complete_onboarding("user-123")

    assert result is True
    sync_mock.assert_awaited_once_with(
        user_id="user-123",
        persona="solopreneur",
        business_context=profile_data["business_context"],
        preferences=profile_data["preferences"],
        agent_name="Ava",
        agent_setup={"focus_areas": ["sales", "content"]},
    )
    schedule_mock.assert_awaited_once_with(
        "user-123",
        "solopreneur",
        profile_data["business_context"],
    )
    mock_cache.invalidate_user_all.assert_awaited_once_with("user-123")
    mock_agent_factory.invalidate_cache.assert_called_once_with("user-123")
