# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: financial operations.yaml parses and binds to OperationsConfig."""

from pathlib import Path

from app.agents.runtime.operations_config import OperationsConfig

OPS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "financial"
    / "operations.yaml"
)


def test_operations_yaml_loads_with_expected_values():
    ops = OperationsConfig.load(OPS_PATH)

    assert ops.agent_id == "financial"
    assert ops.model.primary == "gemini-2.5-pro"
    assert ops.model.fallback == "gemini-2.5-flash"
    assert ops.retry.max_attempts == 5
    assert ops.retry.backoff_initial_s == 2
    assert ops.retry.backoff_multiplier == 2
    assert ops.retry.backoff_max_s == 60
    assert ops.approval.required_above_usd == 1000
    assert ops.approval.required_for_external_send is True
    assert ops.research.max_iterations == 3
    assert ops.research.required_source_min == 3
    assert ops.audit.fail_on_any_unmet_criterion is True
    assert ops.audit.escalate_on_partial is False
    assert "finance:*" in ops.skills.allowed_ids
    assert "data:*" in ops.skills.allowed_ids
    # NOTE: underscore form — matches the canonical skill name registered in
    # app/skills/professional_finance_legal.py. Task 111's contract test
    # verifies every pattern resolves to at least one real skill.
    assert "compliance:legal_risk_assessment" in ops.skills.allowed_ids
    assert ops.skills.injection.top_k == 5
    assert ops.skills.injection.similarity_floor == 0.65
    assert "validation" in ops.initiative.phases_owned
    assert "build" in ops.initiative.phases_owned
    assert ops.initiative.can_advance_phase is True
    assert ops.initiative.can_close is False
    assert ops.memory.history_retention_months == 18
    assert ops.memory.retrieval_top_k == 4
    assert ops.compaction.trigger_token_count == 80000
    assert ops.compaction.keep_last_n_turns == 12
    assert ops.routing.last_resort_default == "initiative"
