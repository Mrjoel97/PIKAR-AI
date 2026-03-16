import asyncio
import json
from unittest.mock import AsyncMock

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
    client.aclose = AsyncMock()
    service._redis = client
    service._connected = True
    return service, client


def test_persona_namespace_round_trip_matches_skill_loader_contract():
    service, client = _connected_cache_service()
    payload = json.dumps([
        {
            "name": "ops-playbook",
            "description": "Operations skill",
            "knowledge": "Playbook body",
            "agent_ids": ["OPS"],
        }
    ])
    client.get.return_value = payload

    wrote = _run(service.set_user_persona("skills:all", payload, ttl=3600))
    read_result = _run(service.get_user_persona("skills:all"))

    assert wrote is True
    client.set.assert_awaited_with("persona:skills:all", payload, ex=3600)
    assert read_result == CacheResult.hit(payload)
    client.get.assert_awaited_with("persona:skills:all")


def test_skill_catalog_cache_miss_uses_persona_namespace_and_returns_cache_result():
    service, client = _connected_cache_service()
    client.get.return_value = None

    result = _run(service.get_user_persona("skills:all"))

    assert result == CacheResult.miss()
    client.get.assert_awaited_with("persona:skills:all")
    client.incr.assert_awaited_with("stats:misses")
