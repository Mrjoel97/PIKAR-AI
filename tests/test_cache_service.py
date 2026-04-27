import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cache import (
    REDIS_KEY_PREFIXES,
    CacheResult,
    get_cache_service,
    invalidate_cache_service,
)


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


# ---------------------------------------------------------------------------
# Singleton / lifecycle tests
# ---------------------------------------------------------------------------


def test_get_cache_service_returns_singleton_instance():
    first = get_cache_service()
    second = get_cache_service()

    assert first is second


def test_invalidate_cache_service_resets_singleton_instance():
    first = get_cache_service()
    invalidate_cache_service()
    second = get_cache_service()

    assert first is not second


# ---------------------------------------------------------------------------
# R1/R2: user_config key uses pikar:user_config: prefix
# ---------------------------------------------------------------------------


def test_get_user_config_hit_returns_cache_result():
    """R1: get_user_config reads key pikar:user_config:{id}."""
    service, client = _connected_cache_service()
    user_id = "user_123"
    expected_config = {"agent_name": "TestAgent"}
    client.get.return_value = json.dumps(expected_config)

    result = _run(service.get_user_config(user_id))

    assert result == CacheResult.hit(expected_config)
    expected_key = f"{REDIS_KEY_PREFIXES['user_config']}{user_id}"
    client.get.assert_awaited_with(expected_key)
    client.incr.assert_awaited_with("pikar:stats:hits")


def test_get_user_config_miss_returns_cache_result():
    """R1: get_user_config on miss reads pikar:user_config:{id}."""
    service, client = _connected_cache_service()
    user_id = "user_123"
    client.get.return_value = None

    result = _run(service.get_user_config(user_id))

    assert result == CacheResult.miss()
    expected_key = f"{REDIS_KEY_PREFIXES['user_config']}{user_id}"
    client.get.assert_awaited_with(expected_key)
    client.incr.assert_awaited_with("pikar:stats:misses")


def test_get_user_config_error_returns_error_result():
    service, client = _connected_cache_service()
    client.get.side_effect = Exception("Redis error")

    result = _run(service.get_user_config("user_123"))

    assert result.is_error is True
    assert result.error == "Redis error"


def test_set_user_config_uses_default_ttl():
    """R2: set_user_config writes key pikar:user_config:{id}."""
    service, client = _connected_cache_service()
    user_id = "user_123"
    config = {"key": "value"}

    success = _run(service.set_user_config(user_id, config))

    assert success is True
    expected_key = f"{REDIS_KEY_PREFIXES['user_config']}{user_id}"
    client.set.assert_awaited_with(
        expected_key,
        json.dumps(config),
        ex=3600,
    )


def test_user_config_key_uses_namespace():
    """R1+R2: user_config keys start with pikar:user_config: prefix."""
    service, client = _connected_cache_service()
    user_id = "abc"
    config = {"x": 1}
    client.get.return_value = None

    _run(service.set_user_config(user_id, config))

    call_args = client.set.call_args
    key_used = call_args[0][0]
    assert key_used.startswith("pikar:user_config:"), (
        f"Expected pikar:user_config: prefix, got: {key_used!r}"
    )


def test_invalidate_user_config_uses_namespace():
    """R7: invalidate_user_config deletes key pikar:user_config:{id}."""
    service, client = _connected_cache_service()
    user_id = "user_123"

    result = _run(service.invalidate_user_config(user_id))

    assert result is True
    expected_key = f"{REDIS_KEY_PREFIXES['user_config']}{user_id}"
    client.delete.assert_awaited_with(expected_key)


# ---------------------------------------------------------------------------
# R3/R4/R8: session_metadata key uses pikar:session: prefix
# ---------------------------------------------------------------------------


def test_get_session_metadata_uses_namespace():
    """R3: get_session_metadata reads key pikar:session:{id}."""
    service, client = _connected_cache_service()
    session_id = "sess_abc"
    meta = {"user_id": "u1"}
    client.get.return_value = json.dumps(meta)

    result = _run(service.get_session_metadata(session_id))

    assert result == CacheResult.hit(meta)
    expected_key = f"{REDIS_KEY_PREFIXES['session_meta']}{session_id}"
    client.get.assert_awaited_with(expected_key)


def test_set_session_metadata_uses_namespace():
    """R4: set_session_metadata writes key pikar:session:{id}."""
    service, client = _connected_cache_service()
    session_id = "sess_abc"
    meta = {"user_id": "u1"}

    result = _run(service.set_session_metadata(session_id, meta))

    assert result is True
    expected_key = f"{REDIS_KEY_PREFIXES['session_meta']}{session_id}"
    client.set.assert_awaited_with(expected_key, json.dumps(meta), ex=1800)


def test_invalidate_session_uses_namespace():
    """R8: invalidate_session deletes key pikar:session:{id}."""
    service, client = _connected_cache_service()
    session_id = "sess_abc"

    result = _run(service.invalidate_session(session_id))

    assert result is True
    expected_key = f"{REDIS_KEY_PREFIXES['session_meta']}{session_id}"
    client.delete.assert_awaited_with(expected_key)


def test_session_metadata_key_uses_namespace():
    """R3+R4: session metadata keys start with pikar:session: prefix."""
    service, client = _connected_cache_service()
    meta = {"x": 1}
    _run(service.set_session_metadata("sess_xyz", meta))

    call_args = client.set.call_args
    key_used = call_args[0][0]
    assert key_used.startswith("pikar:session:"), (
        f"Expected pikar:session: prefix, got: {key_used!r}"
    )


# ---------------------------------------------------------------------------
# R5/R6: persona key uses pikar:persona: prefix
# ---------------------------------------------------------------------------


def test_get_user_persona_uses_namespace():
    """R5: get_user_persona reads key pikar:persona:{id}."""
    service, client = _connected_cache_service()
    user_id = "user_456"
    client.get.return_value = "ceo"

    result = _run(service.get_user_persona(user_id))

    assert result == CacheResult.hit("ceo")
    expected_key = f"{REDIS_KEY_PREFIXES['persona']}{user_id}"
    client.get.assert_awaited_with(expected_key)


def test_set_user_persona_uses_namespace():
    """R6: set_user_persona writes key pikar:persona:{id}."""
    service, client = _connected_cache_service()
    user_id = "user_456"

    result = _run(service.set_user_persona(user_id, "ceo"))

    assert result is True
    expected_key = f"{REDIS_KEY_PREFIXES['persona']}{user_id}"
    client.set.assert_awaited_with(expected_key, "ceo", ex=7200)


def test_user_persona_key_uses_namespace():
    """R5+R6: persona keys start with pikar:persona: prefix."""
    service, client = _connected_cache_service()
    _run(service.set_user_persona("u99", "admin"))

    call_args = client.set.call_args
    key_used = call_args[0][0]
    assert key_used.startswith("pikar:persona:"), (
        f"Expected pikar:persona: prefix, got: {key_used!r}"
    )


# ---------------------------------------------------------------------------
# R9/R10: get_generic and set_generic handle None Redis gracefully
# ---------------------------------------------------------------------------


def test_get_generic_returns_miss_when_redis_none():
    """R9: get_generic returns CacheResult (not AttributeError) when _redis is None."""
    service = get_cache_service()
    service._redis = None
    service._connected = False

    result = _run(service.get_generic("some:key"))

    # Must not raise AttributeError — must return a CacheResult
    assert isinstance(result, CacheResult)
    assert result.found is False


def test_set_generic_returns_false_when_redis_none():
    """R10: set_generic returns False (not AttributeError) when _redis is None."""
    service = get_cache_service()
    service._redis = None
    service._connected = False

    result = _run(service.set_generic("some:key", {"data": 1}))

    assert result is False


def test_get_generic_returns_hit_when_connected():
    """get_generic returns CacheResult.hit when Redis has the key."""
    service, client = _connected_cache_service()
    client.get.return_value = json.dumps({"foo": "bar"})

    result = _run(service.get_generic("arb:key"))

    assert result.found is True
    assert result.value == {"foo": "bar"}


def test_set_generic_returns_true_when_connected():
    """set_generic returns True when Redis is available."""
    service, client = _connected_cache_service()

    result = _run(service.set_generic("arb:key", {"x": 1}, ttl=120))

    assert result is True
    client.set.assert_awaited_once()


# ---------------------------------------------------------------------------
# Stats / hit counters use namespaced keys
# ---------------------------------------------------------------------------


def test_get_stats_returns_metrics():
    service, client = _connected_cache_service()
    client.get.side_effect = ["10", "5"]

    stats = _run(service.get_stats())

    assert stats["hits"] == 10
    assert stats["misses"] == 5
    assert 66 < stats["hit_rate"] < 67


# ---------------------------------------------------------------------------
# invalidate_user_all uses pipeline with namespaced keys
# ---------------------------------------------------------------------------


def test_invalidate_user_all_uses_pipeline():
    service, client = _connected_cache_service()
    user_id = "user_123"
    pipeline = MagicMock()
    pipeline.execute = AsyncMock(return_value=True)
    client.pipeline = MagicMock(return_value=pipeline)

    success = _run(service.invalidate_user_all(user_id))

    assert success is True
    pipeline.delete.assert_any_call(f"{REDIS_KEY_PREFIXES['user_config']}{user_id}")
    pipeline.delete.assert_any_call(f"{REDIS_KEY_PREFIXES['persona']}{user_id}")
    pipeline.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# Concurrency / connection tests
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Environment / runtime detection tests
# ---------------------------------------------------------------------------


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
