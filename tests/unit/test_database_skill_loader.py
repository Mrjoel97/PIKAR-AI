from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.services.cache import CacheResult
from app.skills.database_loader import DatabaseSkillLoader
from app.skills.registry import AgentID


class _FakeSkillsQuery:
    def __init__(self, rows: list[dict]):
        self._rows = list(rows)

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key: str, value):
        self._rows = [row for row in self._rows if row.get(key) == value]
        return self

    def contains(self, key: str, values: list[str]):
        self._rows = [
            row
            for row in self._rows
            if all(value in (row.get(key) or []) for value in values)
        ]
        return self

    def or_(self, *_args, **_kwargs):
        return self

    def limit(self, count: int):
        self._rows = self._rows[:count]
        return self

    def execute(self):
        return SimpleNamespace(data=list(self._rows))


class _FakeClient:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def table(self, name: str):
        assert name == "skills"
        return _FakeSkillsQuery(self._rows)


def _build_mock_loader() -> tuple[DatabaseSkillLoader, MagicMock, MagicMock]:
    client = MagicMock()
    query = MagicMock(name="skills_query")
    query.select.return_value = query
    query.eq.return_value = query
    query.contains.return_value = query
    query.or_.return_value = query
    query.limit.return_value = query
    query.insert.return_value = query
    client.table.return_value = query
    loader = DatabaseSkillLoader(client)
    return loader, client, query


@pytest.mark.asyncio
async def test_get_all_skills_uses_content_fallback_normalizes_agent_ids_and_public_cache_writer():
    loader, _client, query = _build_mock_loader()
    loader.cache = Mock(
        get_user_persona=AsyncMock(return_value=CacheResult.miss()),
        set_user_persona=AsyncMock(return_value=True),
    )
    response = SimpleNamespace(
        data=[
            {
                "name": "ops-playbook",
                "description": "Operations skill",
                "category": "operations",
                "content": "Legacy markdown body",
                "metadata": {"source": "seed"},
                "agent_ids": ["ops", "DATA", "INVALID"],
            }
        ]
    )

    with patch("app.skills.database_loader.execute_async", new=AsyncMock(return_value=response)) as mock_execute:
        skills = await loader.get_all_skills()

    assert len(skills) == 1
    assert skills[0].knowledge == "Legacy markdown body"
    assert skills[0].agent_ids == [AgentID.OPS, AgentID.DATA]
    mock_execute.assert_awaited_once_with(query, op_name="skills.get_all")
    loader.cache.set_user_persona.assert_awaited_once()
    cache_args = loader.cache.set_user_persona.await_args
    assert cache_args.args[0] == "skills:all"
    assert cache_args.kwargs["ttl"] == 3600


@pytest.mark.asyncio
async def test_get_all_skills_prefers_cached_payload_without_hitting_supabase():
    loader, client, _query = _build_mock_loader()
    loader.cache = Mock(
        get_user_persona=AsyncMock(
            return_value=CacheResult.hit(
                '[{"name": "cached-skill", "description": "Cached", "category": "ops", "knowledge": "Cached body", "metadata": {}, "agent_ids": ["OPS"]}]'
            )
        ),
        set_user_persona=AsyncMock(return_value=True),
    )

    skills = await loader.get_all_skills()

    assert [skill.name for skill in skills] == ["cached-skill"]
    assert skills[0].agent_ids == [AgentID.OPS]
    client.table.assert_not_called()
    loader.cache.set_user_persona.assert_not_called()


@pytest.mark.asyncio
async def test_get_skills_for_agent_skips_restricted_rows():
    loader = DatabaseSkillLoader(
        _FakeClient(
            [
                {
                    "name": "ops-visible",
                    "description": "Visible skill",
                    "category": "operations",
                    "knowledge": "Visible knowledge",
                    "metadata": {},
                    "agent_ids": ["OPS"],
                    "is_restricted": False,
                },
                {
                    "name": "ops-hidden",
                    "description": "Restricted skill",
                    "category": "operations",
                    "knowledge": "Restricted knowledge",
                    "metadata": {},
                    "agent_ids": ["OPS"],
                    "is_restricted": True,
                },
            ]
        )
    )
    loader.cache = Mock(get_user_persona=AsyncMock(return_value=CacheResult.miss()))

    skills = await loader.get_skills_for_agent(AgentID.OPS)

    assert [skill.name for skill in skills] == ["ops-visible"]


@pytest.mark.asyncio
async def test_log_skill_usage_uses_async_execute():
    loader, _client, query = _build_mock_loader()
    loader.cache = Mock()

    with patch("app.skills.database_loader.execute_async", new=AsyncMock(return_value=SimpleNamespace(data=[]))) as mock_execute:
        result = await loader.log_skill_usage(
            skill_id="skill-1",
            user_id="user-1",
            agent_id="OPS",
            session_id="session-1",
            duration_ms=25,
            success=True,
        )

    assert result is True
    mock_execute.assert_awaited_once_with(query, op_name="skills.log_usage")
