from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

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


@pytest.mark.asyncio
async def test_get_all_skills_uses_content_fallback_and_normalizes_agent_ids():
    loader = DatabaseSkillLoader(
        _FakeClient(
            [
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
    )
    loader.cache = Mock(
        get_user_persona=AsyncMock(return_value=None),
        _redis=Mock(set=AsyncMock()),
    )

    skills = await loader.get_all_skills()

    assert len(skills) == 1
    assert skills[0].knowledge == "Legacy markdown body"
    assert skills[0].agent_ids == [AgentID.OPS, AgentID.DATA]
    loader.cache._redis.set.assert_awaited_once()


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
    loader.cache = Mock(get_user_persona=AsyncMock(return_value=None), _redis=Mock(set=AsyncMock()))

    skills = await loader.get_skills_for_agent(AgentID.OPS)

    assert [skill.name for skill in skills] == ["ops-visible"]
