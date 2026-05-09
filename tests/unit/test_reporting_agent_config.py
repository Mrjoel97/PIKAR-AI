"""Tests verifying the DataReportingAgent uses the DEEP_AGENT_CONFIG profile."""

from __future__ import annotations

from app.agents.reporting.agent import (
    create_data_reporting_agent,
    data_reporting_agent,
)
from app.agents.shared import DEEP_AGENT_CONFIG


def test_data_reporting_agent_singleton_uses_deep_config() -> None:
    """The module-level singleton must declare DEEP_AGENT_CONFIG explicitly."""
    assert data_reporting_agent.generate_content_config is DEEP_AGENT_CONFIG


def test_create_data_reporting_agent_factory_uses_deep_config() -> None:
    """Factory-built instances must declare DEEP_AGENT_CONFIG explicitly."""
    agent = create_data_reporting_agent()
    assert agent.generate_content_config is DEEP_AGENT_CONFIG
