# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: customer-support operations.yaml parses and binds to OperationsConfig."""

from pathlib import Path

from app.agents.runtime.operations_config import OperationsConfig

OPS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "customer_support"
    / "operations.yaml"
)


def test_operations_yaml_loads_with_expected_values():
    ops = OperationsConfig.load(OPS_PATH)

    assert ops.agent_id == "customer_support"
    assert ops.model.primary == "gemini-2.5-pro"
    assert ops.model.fallback == "gemini-2.5-flash"
    assert ops.retry.max_attempts == 5
    assert ops.approval.required_for_external_send is True
    assert ops.approval.required_above_usd is None
    assert "support:*" in ops.skills.allowed_ids
    assert "compliance:legal_risk_assessment" in ops.skills.allowed_ids
    assert "build" in ops.initiative.phases_owned
    assert "scale" in ops.initiative.phases_owned
    assert ops.initiative.can_advance_phase is True
    assert ops.initiative.can_close is False
    assert ops.routing.last_resort_default == "direct"
