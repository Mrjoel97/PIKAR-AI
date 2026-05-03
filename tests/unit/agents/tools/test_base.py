from __future__ import annotations

import enum
import inspect

from app.agents.tools.base import agent_tool


class NumericToolState(enum.IntEnum):
    IDLE = 0
    ACTIVE = 1


def test_agent_tool_serializes_numeric_enum_return_to_string():
    @agent_tool
    def choose_state() -> NumericToolState:
        return NumericToolState.ACTIVE

    assert choose_state() == "active"
    assert choose_state.__annotations__["return"] is str
    assert inspect.signature(choose_state).return_annotation is str
