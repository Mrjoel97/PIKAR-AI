"""Unit tests for ad budget cap integration endpoints."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_budget_cap_uses_bearer_token_for_rls_reads():
    """GET budget-cap should instantiate the service with the caller JWT."""
    from app.routers.integrations import get_budget_cap

    mock_service = AsyncMock()
    mock_service.get_cap = AsyncMock(return_value=750.0)

    with patch(
        "app.services.ad_budget_cap_service.AdBudgetCapService",
        return_value=mock_service,
    ) as service_cls:
        response = await get_budget_cap(
            "google_ads",
            current_user_id="user-1",
            user_token="jwt-abc",
        )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "platform": "google_ads",
        "monthly_cap": 750.0,
    }
    service_cls.assert_called_once_with(user_token="jwt-abc")
    mock_service.get_cap.assert_awaited_once_with(
        user_id="user-1",
        platform="google_ads",
    )
