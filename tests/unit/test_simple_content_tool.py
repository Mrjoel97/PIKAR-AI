"""Unit tests for simple_create_content tool."""

import pytest
from unittest.mock import AsyncMock, patch


@patch("app.agents.content.tools.ContentService")
@patch("app.agents.content.tools.get_brand_profile", new_callable=AsyncMock)
@patch("app.agents.content.tools.get_current_user_id", return_value="user-123")
@pytest.mark.asyncio
async def test_simple_create_social_post(mock_uid, mock_brand, mock_svc_cls):
    """simple_create_content with content_type='social_post' returns success with draft metadata."""
    from app.agents.content.tools import simple_create_content

    mock_brand.return_value = {
        "success": True,
        "brand_name": "TestBrand",
        "voice_tone": "bold and conversational",
    }
    mock_svc = mock_svc_cls.return_value
    mock_svc.save_content = AsyncMock(
        return_value={"success": True, "ids": ["content-001"]}
    )

    result = await simple_create_content(
        topic="Product launch announcement",
        content_type="social_post",
    )

    assert result["success"] is True
    assert result["content_type"] == "social_post"
    assert result["topic"] == "Product launch announcement"
    assert "brand_context" in result
    assert result["brand_context"]["brand_name"] == "TestBrand"
    assert "prompt_context" in result
    assert result["saved"] is True
    assert result["content_id"] is not None


@patch("app.agents.content.tools.ContentService")
@patch("app.agents.content.tools.get_brand_profile", new_callable=AsyncMock)
@patch("app.agents.content.tools.get_current_user_id", return_value="user-123")
@pytest.mark.asyncio
async def test_simple_create_blog_intro(mock_uid, mock_brand, mock_svc_cls):
    """simple_create_content with content_type='blog_intro' returns blog intro draft."""
    from app.agents.content.tools import simple_create_content

    mock_brand.return_value = {"success": True, "brand_name": "BlogCo", "voice_tone": "authoritative"}
    mock_svc = mock_svc_cls.return_value
    mock_svc.save_content = AsyncMock(
        return_value={"success": True, "ids": ["content-002"]}
    )

    result = await simple_create_content(
        topic="AI in healthcare",
        content_type="blog_intro",
    )

    assert result["success"] is True
    assert result["content_type"] == "blog_intro"
    assert result["prompt_context"]["content_type"] == "blog_intro"


@patch("app.agents.content.tools.ContentService")
@patch("app.agents.content.tools.get_brand_profile", new_callable=AsyncMock)
@patch("app.agents.content.tools.get_current_user_id", return_value="user-123")
@pytest.mark.asyncio
async def test_simple_create_email(mock_uid, mock_brand, mock_svc_cls):
    """simple_create_content with content_type='email' returns email draft."""
    from app.agents.content.tools import simple_create_content

    mock_brand.return_value = {"success": True, "brand_name": "MailCo", "voice_tone": "friendly"}
    mock_svc = mock_svc_cls.return_value
    mock_svc.save_content = AsyncMock(
        return_value={"success": True, "ids": ["content-003"]}
    )

    result = await simple_create_content(
        topic="Welcome new subscribers",
        content_type="email",
    )

    assert result["success"] is True
    assert result["content_type"] == "email"


@patch("app.agents.content.tools.ContentService")
@patch("app.agents.content.tools.get_brand_profile", new_callable=AsyncMock)
@patch("app.agents.content.tools.get_current_user_id", return_value="user-123")
@pytest.mark.asyncio
async def test_simple_create_with_platform(mock_uid, mock_brand, mock_svc_cls):
    """simple_create_content with platform='twitter' includes platform in metadata."""
    from app.agents.content.tools import simple_create_content

    mock_brand.return_value = {"success": True, "brand_name": "TweetCo", "voice_tone": "punchy"}
    mock_svc = mock_svc_cls.return_value
    mock_svc.save_content = AsyncMock(
        return_value={"success": True, "ids": ["content-004"]}
    )

    result = await simple_create_content(
        topic="Flash sale",
        content_type="social_post",
        platform="twitter",
    )

    assert result["success"] is True
    assert result["platform"] == "twitter"
    assert result["prompt_context"]["platform"] == "twitter"


@patch("app.agents.content.tools.ContentService")
@patch("app.agents.content.tools.get_brand_profile", new_callable=AsyncMock)
@patch("app.agents.content.tools.get_current_user_id", return_value="user-123")
@pytest.mark.asyncio
async def test_simple_create_calls_save_content(mock_uid, mock_brand, mock_svc_cls):
    """simple_create_content calls ContentService.save_content to persist the draft."""
    from app.agents.content.tools import simple_create_content

    mock_brand.return_value = {"success": True, "brand_name": "SaveCo", "voice_tone": "warm"}
    mock_svc = mock_svc_cls.return_value
    mock_svc.save_content = AsyncMock(
        return_value={"success": True, "ids": ["content-005"]}
    )

    await simple_create_content(
        topic="Year in review",
        content_type="headline",
    )

    mock_svc.save_content.assert_called_once()
    call_kwargs = mock_svc.save_content.call_args[1]
    assert call_kwargs["agent_id"] == "content-agent"
    assert call_kwargs["user_id"] == "user-123"


@patch("app.agents.content.tools.ContentService")
@patch("app.agents.content.tools.get_brand_profile", new_callable=AsyncMock)
@patch("app.agents.content.tools.get_current_user_id", return_value="user-123")
@pytest.mark.asyncio
async def test_simple_create_loads_brand_profile(mock_uid, mock_brand, mock_svc_cls):
    """simple_create_content loads brand profile and includes it in response context."""
    from app.agents.content.tools import simple_create_content

    mock_brand.return_value = {
        "success": True,
        "brand_name": "BrandyMcBrandFace",
        "voice_tone": "edgy and irreverent",
    }
    mock_svc = mock_svc_cls.return_value
    mock_svc.save_content = AsyncMock(
        return_value={"success": True, "ids": ["content-006"]}
    )

    result = await simple_create_content(
        topic="Brand manifesto",
        content_type="tagline",
    )

    mock_brand.assert_called_once()
    assert result["brand_context"]["brand_name"] == "BrandyMcBrandFace"
    assert result["brand_context"]["voice_tone"] == "edgy and irreverent"


@patch("app.agents.content.tools.ContentService")
@patch("app.agents.content.tools.get_brand_profile", new_callable=AsyncMock)
@patch("app.agents.content.tools.get_current_user_id", return_value="user-123")
@pytest.mark.asyncio
async def test_simple_create_brand_profile_failure_not_blocking(
    mock_uid, mock_brand, mock_svc_cls
):
    """simple_create_content still works when brand profile fails to load."""
    from app.agents.content.tools import simple_create_content

    mock_brand.side_effect = Exception("DB connection error")
    mock_svc = mock_svc_cls.return_value
    mock_svc.save_content = AsyncMock(
        return_value={"success": True, "ids": ["content-007"]}
    )

    result = await simple_create_content(
        topic="Quick update",
        content_type="caption",
    )

    assert result["success"] is True
    assert result["brand_context"] == {}
