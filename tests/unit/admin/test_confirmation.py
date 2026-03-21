"""Unit tests for confirmation token store/consume service.

Tests verify:
- store_confirmation_token stores in Redis with correct key and TTL
- consume_confirmation_token returns stored payload and deletes it atomically
- Second consume returns None (single-use via GETDEL)
- Expired/missing token returns None
- Redis unavailable: store returns False, consume returns None gracefully
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


_STORE_FN = "app.services.confirmation_tokens.store_confirmation_token"
_CONSUME_FN = "app.services.confirmation_tokens.consume_confirmation_token"
_CACHE_PATCH = "app.services.confirmation_tokens.get_cache_service"

_TOKEN = "test-token-uuid-1234"
_ACTION = {"action": "check_system_health", "risk_level": "low"}
_USER_ID = "admin-user-abc"
_PAYLOAD = json.dumps({"action_details": _ACTION, "admin_user_id": _USER_ID})


@pytest.fixture
def mock_redis():
    """Mock redis.asyncio.Redis client with store/get/getdel support."""
    r = AsyncMock()
    r.set = AsyncMock(return_value=True)
    r.getdel = AsyncMock(return_value=_PAYLOAD)
    return r


@pytest.fixture
def mock_cache_with_redis(mock_redis):
    """Mock CacheService that returns the mock redis client."""
    cache = MagicMock()
    cache._get_redis = AsyncMock(return_value=mock_redis)
    return cache


@pytest.fixture
def mock_cache_no_redis():
    """Mock CacheService where Redis is unavailable (returns None)."""
    cache = MagicMock()
    cache._get_redis = AsyncMock(return_value=None)
    return cache


@pytest.mark.asyncio
async def test_store_token(mock_cache_with_redis, mock_redis):
    """store_confirmation_token stores in Redis with key 'admin:confirm:{token}' and 300s TTL."""
    with patch(_CACHE_PATCH, return_value=mock_cache_with_redis):
        from app.services.confirmation_tokens import store_confirmation_token

        result = await store_confirmation_token(_TOKEN, _ACTION, _USER_ID)

    assert result is True
    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args
    # First positional arg is the key
    key = call_args[0][0]
    assert key == f"admin:confirm:{_TOKEN}"
    # TTL should be 300
    assert call_args[1].get("ex") == 300 or (
        len(call_args[0]) > 2 and call_args[0][2] == 300
    )


@pytest.mark.asyncio
async def test_store_token_payload_structure(mock_cache_with_redis, mock_redis):
    """store_confirmation_token stores JSON payload with action_details and admin_user_id."""
    with patch(_CACHE_PATCH, return_value=mock_cache_with_redis):
        from app.services.confirmation_tokens import store_confirmation_token

        await store_confirmation_token(_TOKEN, _ACTION, _USER_ID)

    call_args = mock_redis.set.call_args
    raw_payload = call_args[0][1]
    payload = json.loads(raw_payload)
    assert payload["action_details"] == _ACTION
    assert payload["admin_user_id"] == _USER_ID


@pytest.mark.asyncio
async def test_consume_token_success(mock_cache_with_redis, mock_redis):
    """After storing, consume_confirmation_token returns the stored payload."""
    with patch(_CACHE_PATCH, return_value=mock_cache_with_redis):
        from app.services.confirmation_tokens import consume_confirmation_token

        result = await consume_confirmation_token(_TOKEN)

    assert result is not None
    assert result["action_details"] == _ACTION
    assert result["admin_user_id"] == _USER_ID
    mock_redis.getdel.assert_called_once_with(f"admin:confirm:{_TOKEN}")


@pytest.mark.asyncio
async def test_consume_token_double(mock_cache_with_redis, mock_redis):
    """Second consume returns None (atomic single-use via GETDEL)."""
    # First call returns payload, second call returns None (already consumed)
    mock_redis.getdel = AsyncMock(side_effect=[_PAYLOAD, None])

    with patch(_CACHE_PATCH, return_value=mock_cache_with_redis):
        from app.services.confirmation_tokens import consume_confirmation_token

        first = await consume_confirmation_token(_TOKEN)
        second = await consume_confirmation_token(_TOKEN)

    assert first is not None
    assert second is None


@pytest.mark.asyncio
async def test_consume_token_expired(mock_cache_with_redis, mock_redis):
    """Token not in Redis (expired or never stored) returns None."""
    mock_redis.getdel = AsyncMock(return_value=None)

    with patch(_CACHE_PATCH, return_value=mock_cache_with_redis):
        from app.services.confirmation_tokens import consume_confirmation_token

        result = await consume_confirmation_token("nonexistent-token")

    assert result is None


@pytest.mark.asyncio
async def test_store_token_no_redis(mock_cache_no_redis):
    """Redis unavailable: store_confirmation_token returns False gracefully."""
    with patch(_CACHE_PATCH, return_value=mock_cache_no_redis):
        from app.services.confirmation_tokens import store_confirmation_token

        result = await store_confirmation_token(_TOKEN, _ACTION, _USER_ID)

    assert result is False


@pytest.mark.asyncio
async def test_consume_token_no_redis(mock_cache_no_redis):
    """Redis unavailable: consume_confirmation_token returns None gracefully."""
    with patch(_CACHE_PATCH, return_value=mock_cache_no_redis):
        from app.services.confirmation_tokens import consume_confirmation_token

        result = await consume_confirmation_token(_TOKEN)

    assert result is None
