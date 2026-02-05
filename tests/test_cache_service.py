import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.cache import CacheService, get_cache_service, invalidate_cache_service

@pytest.fixture
def mock_redis():
    with patch("redis.asyncio.Redis", new_callable=MagicMock) as mock_cls:
        client = AsyncMock()
        mock_cls.return_value = client
        yield client

@pytest.fixture
def cache_service(mock_redis):
    # Reset singleton
    invalidate_cache_service()
    service = get_cache_service()
    # Inject mock
    service._redis = mock_redis
    service._connected = True
    return service

@pytest.mark.asyncio
async def test_initialization(mock_redis):
    invalidate_cache_service()
    service = get_cache_service()
    # Verify redis init was called
    assert service._redis is not None

@pytest.mark.asyncio
async def test_get_user_config_hit(cache_service, mock_redis):
    user_id = "user_123"
    expected_config = {"agent_name": "TestAgent"}
    mock_redis.get.return_value = json.dumps(expected_config)
    
    result = await cache_service.get_user_config(user_id)
    
    assert result == expected_config
    mock_redis.get.assert_called_with(f"user_config:{user_id}")
    mock_redis.incr.assert_called_with("stats:hits")

@pytest.mark.asyncio
async def test_get_user_config_miss(cache_service, mock_redis):
    user_id = "user_123"
    mock_redis.get.return_value = None
    
    result = await cache_service.get_user_config(user_id)
    
    assert result is None
    mock_redis.get.assert_called_with(f"user_config:{user_id}")
    mock_redis.incr.assert_called_with("stats:misses")

@pytest.mark.asyncio
async def test_get_user_config_error(cache_service, mock_redis):
    user_id = "user_123"
    mock_redis.get.side_effect = Exception("Redis error")
    
    result = await cache_service.get_user_config(user_id)
    
    assert result is None

@pytest.mark.asyncio
async def test_set_user_config(cache_service, mock_redis):
    user_id = "user_123"
    config = {"key": "value"}
    
    await cache_service.set_user_config(user_id, config)
    
    mock_redis.set.assert_called_with(
        f"user_config:{user_id}",
        json.dumps(config),
        ex=3600
    )

@pytest.mark.asyncio
async def test_invalidate_user_config(cache_service, mock_redis):
    user_id = "user_123"
    
    await cache_service.invalidate_user_config(user_id)
    
    mock_redis.delete.assert_called_with(f"user_config:{user_id}")

@pytest.mark.asyncio
async def test_get_session_metadata_hit(cache_service, mock_redis):
    session_id = "sess_123"
    metadata = {"last_active": "now"}
    mock_redis.get.return_value = json.dumps(metadata)
    
    result = await cache_service.get_session_metadata(session_id)
    
    assert result == metadata
    mock_redis.get.assert_called_with(f"session:{session_id}")

@pytest.mark.asyncio
async def test_set_session_metadata(cache_service, mock_redis):
    session_id = "sess_123"
    metadata = {"key": "val"}
    ttl = 60
    
    await cache_service.set_session_metadata(session_id, metadata, ttl=ttl)
    
    mock_redis.set.assert_called_with(
        f"session:{session_id}",
        json.dumps(metadata),
        ex=ttl
    )

@pytest.mark.asyncio
async def test_invalidate_session(cache_service, mock_redis):
    session_id = "sess_123"
    
    await cache_service.invalidate_session(session_id)
    
    mock_redis.delete.assert_called_with(f"session:{session_id}")

@pytest.mark.asyncio
async def test_get_stats(cache_service, mock_redis):
    mock_redis.info.return_value = {
        "redis_version": "7.0",
        "used_memory_human": "1M",
        "connected_clients": 5
    }
    mock_redis.get.side_effect = ["10", "5"] # hits, misses
    
    stats = await cache_service.get_stats()
    
    assert stats["hits"] == 10
    assert stats["misses"] == 5
    # 10 / 15 = 66.666...
    assert 66 < stats["hit_rate"] < 67

@pytest.mark.asyncio
async def test_invalidate_user_all(cache_service, mock_redis):
    user_id = "user_123"
    mock_pipeline = MagicMock()
    # Important: pipeline() is synchronous in redis-py, so we must replace the AsyncMock default
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
    
    await cache_service.invalidate_user_all(user_id)
    
    mock_pipeline.delete.assert_any_call(f"user_config:{user_id}")
    mock_pipeline.delete.assert_any_call(f"persona:{user_id}")
    mock_pipeline.execute.assert_called_once()
