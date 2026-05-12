# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: compliance operations.yaml parses and binds to OperationsConfig."""

from pathlib import Path

from app.agents.runtime.operations_config import OperationsConfig

OPS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "compliance"
    / "operations.yaml"
)


def test_operations_yaml_loads_with_expected_values():
    ops = OperationsConfig.load(OPS_PATH)

    assert ops.agent_id == "compliance"
    assert ops.model.primary == "gemini-2.5-pro"
    assert ops.approval.required_for_external_send is True
    assert ops.research.max_iterations == 5
    assert ops.research.required_source_min == 5
    assert ops.audit.fail_on_any_unmet_criterion is True
    assert ops.audit.escalate_on_partial is True
    assert "compliance:*" in ops.skills.allowed_ids
    assert "validation" in ops.initiative.phases_owned
    assert ops.initiative.can_advance_phase is False
    assert ops.initiative.can_close is False
    assert ops.memory.history_retention_months == 36
    assert ops.routing.last_resort_default == "direct"
