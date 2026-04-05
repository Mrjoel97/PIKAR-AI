"""Integration test: BYOK save -> resolve -> model creation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.byok_service import BYOKConfig, BYOKService


@pytest.mark.asyncio
async def test_byok_full_flow_save_and_resolve():
    """Test: save BYOK config -> get_model_for_user returns LiteLlm."""
    mock_sb = MagicMock()

    # Mock upsert for save
    upsert_chain = MagicMock()
    upsert_chain.execute = AsyncMock(return_value=MagicMock(data=[{"id": "row-1"}]))
    mock_sb.table.return_value.upsert.return_value = upsert_chain

    service = BYOKService(supabase_client=mock_sb)

    # Save
    result = await service.save_config(
        user_id="test-user",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        api_key="sk-ant-test-key",
    )
    assert result["success"] is True

    # Now mock get_config to return what was saved
    cfg = BYOKConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        api_key="sk-ant-test-key",
    )

    # get_byok_service is imported locally inside get_model_for_user via
    # `from app.services.byok_service import get_byok_service`, so we patch
    # the source module where the function lives.
    with patch("app.services.byok_service.get_byok_service") as mock_svc:
        mock_svc.return_value.get_config = AsyncMock(return_value=cfg)

        from app.agents.shared import get_model_for_user

        model = await get_model_for_user("test-user")

        # Verify it's a LiteLlm model, not Gemini
        from google.adk.models import LiteLlm

        assert isinstance(model, LiteLlm)


@pytest.mark.asyncio
async def test_byok_disabled_user_gets_gemini():
    """When BYOK is not configured, user gets default Gemini."""
    with patch("app.services.byok_service.get_byok_service") as mock_svc:
        mock_svc.return_value.get_config = AsyncMock(return_value=None)

        from app.agents.shared import get_model_for_user

        model = await get_model_for_user("no-byok-user")

        from google.adk.models import Gemini

        assert isinstance(model, Gemini)


@pytest.mark.asyncio
async def test_byok_error_falls_back_to_gemini():
    """If BYOK service errors, user still gets Gemini (graceful degradation)."""
    with patch("app.services.byok_service.get_byok_service") as mock_svc:
        mock_svc.return_value.get_config = AsyncMock(side_effect=Exception("DB down"))

        from app.agents.shared import get_model_for_user

        model = await get_model_for_user("error-user")

        from google.adk.models import Gemini

        assert isinstance(model, Gemini)
