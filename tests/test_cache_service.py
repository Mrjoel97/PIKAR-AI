import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cache import CacheResult, get_cache_service, invalidate_cache_service


def _run(coro):
    return asyncio.run(coro)


def setup_function():
    invalidate_cache_service()


def teardown_function():
    invalidate_cache_service()


def _connected_cache_service():
    service = get_cache_service()
    client = AsyncMock()
    client.ping.return_value = True
    client.info.return_value = {
        "redis_version": "7.0",
        "used_memory_human": "1M",
        "connected_clients": 5,
    }
    client.aclose = AsyncMock()
    service._redis = client
    service._connected = True
    return service, client


def test_get_cache_service_returns_singleton_instance():
    first = get_cache_service()
    second = get_cache_service()

    assert first is second


def test_invalidate_cache_service_resets_singleton_instance():
    first = get_cache_service()
    invalidate_cache_service()
    second = get_cache_service()

    assert first is not second


def test_get_user_config_hit_returns_cache_result():
    service, client = _connected_cache_service()
    user_id = "user_123"
    expected_config = {"agent_name": "TestAgent"}
    client.get.return_value = json.dumps(expected_config)

    result = _run(service.get_user_config(user_id))

    assert result == CacheResult.hit(expected_config)
    client.get.assert_awaited_with(f"user_config:{user_id}")
    client.incr.assert_awaited_with("stats:hits")


def test_get_user_config_miss_returns_cache_result():
    service, client = _connected_cache_service()
    user_id = "user_123"
    client.get.return_value = None

    result = _run(service.get_user_config(user_id))

    assert result == CacheResult.miss()
    client.get.assert_awaited_with(f"user_config:{user_id}")
    client.incr.assert_awaited_with("stats:misses")


def test_get_user_config_error_returns_error_result():
    service, client = _connected_cache_service()
    client.get.side_effect = Exception("Redis error")

    result = _run(service.get_user_config("user_123"))

    assert result.is_error is True
    assert result.error == "Redis error"


def test_set_user_config_uses_default_ttl():
    service, client = _connected_cache_service()
    user_id = "user_123"
    config = {"key": "value"}

    success = _run(service.set_user_config(user_id, config))

    assert success is True
    client.set.assert_awaited_with(
        f"user_config:{user_id}",
        json.dumps(config),
        ex=3600,
    )


def test_get_stats_returns_metrics():
    service, client = _connected_cache_service()
    client.get.side_effect = ["10", "5"]

    stats = _run(service.get_stats())

    assert stats["hits"] == 10
    assert stats["misses"] == 5
    assert 66 < stats["hit_rate"] < 67


def test_invalidate_user_all_uses_pipeline():
    service, client = _connected_cache_service()
    user_id = "user_123"
    pipeline = MagicMock()
    pipeline.execute = AsyncMock(return_value=True)
    client.pipeline = MagicMock(return_value=pipeline)

    success = _run(service.invalidate_user_all(user_id))

    assert success is True
    pipeline.delete.assert_any_call(f"user_config:{user_id}")
    pipeline.delete.assert_any_call(f"persona:{user_id}")
    pipeline.execute.assert_awaited_once()


def test_ensure_connection_is_singleflight_under_concurrency():
    async def scenario():
        gate = asyncio.Event()
        client = AsyncMock()
        client.get.return_value = None
        client.aclose = AsyncMock()

        async def delayed_ping():
            await gate.wait()
            return True

        client.ping.side_effect = delayed_ping

        with patch("app.services.cache.redis.Redis", return_value=client) as redis_cls:
            service = get_cache_service()
            tasks = [asyncio.create_task(service.get_user_persona("skills:all")) for _ in range(3)]
            await asyncio.sleep(0)
            gate.set()
            results = await asyncio.gather(*tasks)

        return redis_cls.call_count, client.ping.await_count, results

    call_count, ping_count, results = _run(scenario())

    assert call_count == 1
    assert ping_count == 1
    assert all(result == CacheResult.miss() for result in results)


def test_close_clears_connection_state():
    service, client = _connected_cache_service()

    _run(service.close())

    assert service._connected is False
    assert service._redis is None
    client.aclose.assert_awaited_once()


def test_cloud_run_localhost_defaults_disable_redis():
    with patch.dict(
        os.environ,
        {
            "K_SERVICE": "pikar-ai",
            "REDIS_HOST": "localhost",
        },
        clear=False,
    ):
        invalidate_cache_service()
        service = get_cache_service()
        stats = _run(service.get_stats())

    assert service._redis_enabled is False
    assert stats["status"] == "disabled"
    assert stats["reason"] == "cloud_run_localhost_without_managed_redis"


def test_redis_enabled_env_can_force_disable():
    with patch.dict(
        os.environ,
        {
            "REDIS_ENABLED": "0",
            "REDIS_HOST": "10.0.0.15",
        },
        clear=False,
    ):
        invalidate_cache_service()
        service = get_cache_service()
        stats = _run(service.get_stats())

    assert service._redis_enabled is False
    assert stats["status"] == "disabled"
    assert stats["reason"] == "disabled_by_redis_enabled_env"
