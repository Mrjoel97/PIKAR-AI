"""Tests for app/workflows/graph_validation.py (Phase 110-03).

Pure-functional validator with 5 in-scope rules:
  - Rule 1: exactly one trigger node with zero incoming edges
  - Rule 2: every node reachable from trigger
  - Rule 3: no cycles (Kahn's topological sort)
  - Rule 6: at least one output node
  - Rule 7: per-kind config schema validation

Rules 4 and 5 are stubbed (raise NotImplementedError when strict=True).

Many tests parametrize over the shared fixture at
``tests/fixtures/graph_validation_cases.json`` (B-4 contract). Plan 04's
vitest suite loads the same JSON and parametrizes its
``validateGraphClient()`` tests over the same cases. Either source-of-truth
divergence will be caught by one of the two suites.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.workflows.graph_validation import (
    ValidationError,
    validate_workflow_graph,
)

# ---------- Shared fixture loader (B-4) -------------------------------------

FIXTURE_PATH = (
    Path(__file__).parents[2] / "fixtures" / "graph_validation_cases.json"
)


def _load_cases() -> list[dict]:
    with FIXTURE_PATH.open() as f:
        return json.load(f)


CASES = _load_cases()


# ---------- Parametrized fixture test (B-4 parity contract) -----------------


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_fixture_case(case: dict) -> None:
    """Every case in graph_validation_cases.json must produce its expected_errors.

    Plan 04 loads the same JSON for vitest parity; if behavior changes here,
    Plan 04's frontend tests will diverge until the fixture is updated.
    """
    actual = validate_workflow_graph(
        case["input"]["graph_nodes"], case["input"]["graph_edges"]
    )
    expected = case["expected_errors"]
    assert len(actual) == len(expected), (
        f"Error count mismatch for case '{case['name']}': "
        f"got {[(e.node_id, e.rule, e.message) for e in actual]}, "
        f"expected {expected}"
    )
    for e_expected, e_actual in zip(expected, actual, strict=False):
        assert e_actual.node_id == e_expected["node_id"], (
            f"node_id mismatch for case '{case['name']}': "
            f"got {e_actual.node_id}, expected {e_expected['node_id']}"
        )
        assert e_actual.rule == e_expected["rule"], (
            f"rule mismatch for case '{case['name']}': "
            f"got {e_actual.rule}, expected {e_expected['rule']}"
        )
        if "message_contains" in e_expected:
            assert (
                e_expected["message_contains"].lower()
                in e_actual.message.lower()
            ), (
                f"message_contains '{e_expected['message_contains']}' not "
                f"in '{e_actual.message}' for case '{case['name']}'"
            )


# ---------- Rule 1: single trigger with zero incoming edges -----------------


def test_rule1_no_trigger_returns_graph_level_error() -> None:
    nodes = [
        {"id": "a1", "kind": "agent-action", "label": "A", "config": {"tool_name": "x"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [{"id": "e1", "source": "a1", "target": "o1"}]
    errors = validate_workflow_graph(nodes, edges)
    rule1_errors = [e for e in errors if e.rule == 1]
    assert len(rule1_errors) == 1
    assert rule1_errors[0].node_id is None
    assert "trigger" in rule1_errors[0].message.lower()


def test_rule1_multiple_triggers_flags_extras() -> None:
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T1", "config": {}},
        {"id": "t2", "kind": "trigger", "label": "T2", "config": {}},
        {"id": "t3", "kind": "trigger", "label": "T3", "config": {}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "o1"},
        {"id": "e2", "source": "t2", "target": "o1"},
        {"id": "e3", "source": "t3", "target": "o1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule1_errors = [e for e in errors if e.rule == 1]
    # Two extras flagged (t2 and t3); t1 is the canonical one
    flagged_ids = {e.node_id for e in rule1_errors}
    assert flagged_ids == {"t2", "t3"}


def test_rule1_single_trigger_no_incoming_passes() -> None:
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [{"id": "e1", "source": "t1", "target": "o1"}]
    errors = validate_workflow_graph(nodes, edges)
    rule1_errors = [e for e in errors if e.rule == 1]
    assert rule1_errors == []


# ---------- Rule 2: reachability from trigger -------------------------------


def test_rule2_orphan_node_flagged() -> None:
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "orphan", "kind": "agent-action", "label": "Orphan", "config": {"tool_name": "x"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [{"id": "e1", "source": "t1", "target": "o1"}]
    errors = validate_workflow_graph(nodes, edges)
    rule2_errors = [e for e in errors if e.rule == 2]
    assert len(rule2_errors) == 1
    assert rule2_errors[0].node_id == "orphan"


def test_rule2_all_reachable_passes() -> None:
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "a1", "kind": "agent-action", "label": "A", "config": {"tool_name": "x"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "o1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule2_errors = [e for e in errors if e.rule == 2]
    assert rule2_errors == []


# ---------- Rule 3: no cycles (Kahn's algorithm) ---------------------------


def test_rule3_two_node_cycle_flags_both() -> None:
    """t1 -> a1 -> a2 -> a1 (cycle); also a2 -> o1 to satisfy rule 6."""
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "a1", "kind": "agent-action", "label": "A1", "config": {"tool_name": "x"}},
        {"id": "a2", "kind": "agent-action", "label": "A2", "config": {"tool_name": "x"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "a2"},
        {"id": "e3", "source": "a2", "target": "a1"},
        {"id": "e4", "source": "a2", "target": "o1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule3_errors = [e for e in errors if e.rule == 3]
    flagged = {e.node_id for e in rule3_errors}
    assert {"a1", "a2"} <= flagged


def test_rule3_three_node_cycle_flags_all_three() -> None:
    """t1 -> a1 -> a2 -> a3 -> a1 (3-cycle); a3 -> o1 for rule 6."""
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "a1", "kind": "agent-action", "label": "A1", "config": {"tool_name": "x"}},
        {"id": "a2", "kind": "agent-action", "label": "A2", "config": {"tool_name": "x"}},
        {"id": "a3", "kind": "agent-action", "label": "A3", "config": {"tool_name": "x"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "a2"},
        {"id": "e3", "source": "a2", "target": "a3"},
        {"id": "e4", "source": "a3", "target": "a1"},
        {"id": "e5", "source": "a3", "target": "o1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule3_errors = [e for e in errors if e.rule == 3]
    flagged = {e.node_id for e in rule3_errors}
    assert {"a1", "a2", "a3"} <= flagged


def test_rule3_dag_passes() -> None:
    """Pure DAG should produce zero rule-3 errors."""
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "a1", "kind": "agent-action", "label": "A1", "config": {"tool_name": "x"}},
        {"id": "a2", "kind": "agent-action", "label": "A2", "config": {"tool_name": "x"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "t1", "target": "a2"},
        {"id": "e3", "source": "a1", "target": "o1"},
        {"id": "e4", "source": "a2", "target": "o1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule3_errors = [e for e in errors if e.rule == 3]
    assert rule3_errors == []


# ---------- Rule 6: at least one output -------------------------------------


def test_rule6_no_output_returns_graph_level_error() -> None:
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "a1", "kind": "agent-action", "label": "A", "config": {"tool_name": "x"}},
    ]
    edges = [{"id": "e1", "source": "t1", "target": "a1"}]
    errors = validate_workflow_graph(nodes, edges)
    rule6_errors = [e for e in errors if e.rule == 6]
    assert len(rule6_errors) == 1
    assert rule6_errors[0].node_id is None
    assert "output" in rule6_errors[0].message.lower()


def test_rule6_one_output_passes() -> None:
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [{"id": "e1", "source": "t1", "target": "o1"}]
    errors = validate_workflow_graph(nodes, edges)
    assert [e for e in errors if e.rule == 6] == []


def test_rule6_multiple_outputs_all_pass() -> None:
    """Rule 6 is satisfied with >= 1 output; multiple outputs are OK."""
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "o1", "kind": "output", "label": "O1", "config": {}},
        {"id": "o2", "kind": "output", "label": "O2", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "o1"},
        {"id": "e2", "source": "t1", "target": "o2"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    assert [e for e in errors if e.rule == 6] == []


# ---------- Rule 7: per-kind config validation ------------------------------


def test_rule7_agent_action_missing_tool_name_flagged() -> None:
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "a1", "kind": "agent-action", "label": "A", "config": {"agent_role": "x"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "o1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule7_errors = [e for e in errors if e.rule == 7]
    assert len(rule7_errors) == 1
    assert rule7_errors[0].node_id == "a1"
    assert "tool_name" in rule7_errors[0].message


def test_rule7_agent_action_extra_fields_allowed() -> None:
    """AgentActionConfig has extra='allow' so unknown keys don't fail."""
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {
            "id": "a1",
            "kind": "agent-action",
            "label": "A",
            "config": {"tool_name": "x", "unknown_extra": True, "more_meta": 42},
        },
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "o1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule7_errors = [e for e in errors if e.rule == 7]
    assert rule7_errors == []


def test_rule7_condition_node_empty_config_passes_placeholder() -> None:
    """Phase 110 placeholder: condition kinds accept any dict (extra=allow)."""
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "c1", "kind": "condition", "label": "If?", "config": {}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "c1"},
        {"id": "e2", "source": "c1", "target": "o1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule7_errors = [e for e in errors if e.rule == 7]
    assert rule7_errors == []


def test_rule7_parallel_merge_human_approval_pass_placeholder() -> None:
    """All four Phase 3/4 placeholder kinds save without rule-7 failure."""
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "p1", "kind": "parallel", "label": "P", "config": {}},
        {"id": "m1", "kind": "merge", "label": "M", "config": {}},
        {"id": "h1", "kind": "human-approval", "label": "H", "config": {}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "p1"},
        {"id": "e2", "source": "p1", "target": "m1"},
        {"id": "e3", "source": "m1", "target": "h1"},
        {"id": "e4", "source": "h1", "target": "o1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule7_errors = [e for e in errors if e.rule == 7]
    assert rule7_errors == []


# ---------- Multi-rule / happy-path / edge cases ---------------------------


def test_happy_path_valid_graph_returns_empty_list() -> None:
    """Trigger -> agent-action -> output. Simplest valid graph."""
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {"trigger_type": "manual"}},
        {"id": "a1", "kind": "agent-action", "label": "A", "config": {"tool_name": "x"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "o1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    assert errors == []


def test_multi_rule_violations_emit_all_errors() -> None:
    """Graph with no trigger AND no output AND a cycle -> at least 3 errors."""
    nodes = [
        {"id": "a1", "kind": "agent-action", "label": "A1", "config": {"tool_name": "x"}},
        {"id": "a2", "kind": "agent-action", "label": "A2", "config": {"tool_name": "x"}},
    ]
    edges = [
        {"id": "e1", "source": "a1", "target": "a2"},
        {"id": "e2", "source": "a2", "target": "a1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rules_fired = {e.rule for e in errors}
    # Rule 1 (no trigger), Rule 6 (no output), Rule 3 (cycle) all fire
    assert 1 in rules_fired
    assert 6 in rules_fired
    assert 3 in rules_fired


def test_empty_graph_nodes_returns_rule1_no_trigger() -> None:
    """Empty graph: rule 1 fires (no trigger), rule 6 fires (no output)."""
    errors = validate_workflow_graph([], [])
    assert any(e.rule == 1 and e.node_id is None for e in errors)
    assert any(e.rule == 6 and e.node_id is None for e in errors)


# ---------- strict=True (Phase 3/4 stub) ------------------------------------


def test_strict_true_raises_not_implemented() -> None:
    """strict=True flag exists but rules 4/5 are deferred to Phase 3/4."""
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [{"id": "e1", "source": "t1", "target": "o1"}]
    with pytest.raises(NotImplementedError):
        validate_workflow_graph(nodes, edges, strict=True)


def test_strict_false_default_no_raise() -> None:
    """Default strict=False does not raise on valid graphs."""
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [{"id": "e1", "source": "t1", "target": "o1"}]
    # Should NOT raise
    validate_workflow_graph(nodes, edges)
    validate_workflow_graph(nodes, edges, strict=False)


# ---------- ValidationError model contract ---------------------------------


def test_validation_error_model_has_required_fields() -> None:
    """ValidationError must expose node_id, rule, message."""
    err = ValidationError(node_id="x", rule=1, message="m")
    assert err.node_id == "x"
    assert err.rule == 1
    assert err.message == "m"


def test_validation_error_node_id_can_be_none() -> None:
    """Graph-level errors carry node_id=None."""
    err = ValidationError(node_id=None, rule=1, message="No trigger")
    assert err.node_id is None


# ---------- Rule 4: condition outgoing degree (Phase 111) ------------------


def test_rule_4_handle_set_with_none_value() -> None:
    """Condition with 2 outgoing where one has source_handle=None -> rule 4 fires.

    Set equality {'true', None} != {'true', 'false'}.
    """
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "c1", "kind": "condition", "label": "If?", "config": {}},
        {"id": "o1", "kind": "output", "label": "O1", "config": {}},
        {"id": "o2", "kind": "output", "label": "O2", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "c1"},
        {"id": "e2", "source": "c1", "target": "o1", "source_handle": "true"},
        {"id": "e3", "source": "c1", "target": "o2", "source_handle": None},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule_4_errors = [e for e in errors if e.rule == 4]
    assert len(rule_4_errors) == 1
    assert rule_4_errors[0].node_id == "c1"
    assert "Condition" in rule_4_errors[0].message


def test_rule_4_handle_set_with_missing_key() -> None:
    """Condition with 2 outgoing where one omits source_handle key entirely -> rule 4.

    Missing key behaves identically to None via .get(). Set ends up {'true', None}.
    """
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "c1", "kind": "condition", "label": "If?", "config": {}},
        {"id": "o1", "kind": "output", "label": "O1", "config": {}},
        {"id": "o2", "kind": "output", "label": "O2", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "c1"},
        {"id": "e2", "source": "c1", "target": "o1", "source_handle": "true"},
        # No source_handle key on e3 at all
        {"id": "e3", "source": "c1", "target": "o2"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule_4_errors = [e for e in errors if e.rule == 4]
    assert len(rule_4_errors) == 1
    assert rule_4_errors[0].node_id == "c1"


def test_rule_4_condition_without_outgoing_AND_no_unreachable_collision() -> None:
    """Rule 4 fires independently of rule 2.

    Graph: t1 -> c1 (terminal), t1 -> o1. c1 has 0 outgoing edges but the
    rest of the graph is fully reachable (o1 is reachable directly from t1).
    Rule 4 MUST still fire for c1 regardless of rule-2 reachability state.
    """
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "c1", "kind": "condition", "label": "If?", "config": {}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "c1"},
        {"id": "e2", "source": "t1", "target": "o1"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule_4_errors = [e for e in errors if e.rule == 4]
    rule_2_errors = [e for e in errors if e.rule == 2]
    # No rule 2 errors - every node reachable from t1
    assert rule_2_errors == []
    # Rule 4 still fires on c1 (0 outgoing edges)
    assert len(rule_4_errors) == 1
    assert rule_4_errors[0].node_id == "c1"


def test_rule_4_with_two_conditions_emits_two_errors() -> None:
    """Two invalid condition nodes -> two rule-4 errors in graph_nodes order.

    Determinism check: errors emitted in declaration order, not set iteration.
    """
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        # c_first has 0 outgoing
        {"id": "c_first", "kind": "condition", "label": "First", "config": {}},
        # c_second has 1 outgoing (wrong)
        {"id": "c_second", "kind": "condition", "label": "Second", "config": {}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "c_first"},
        {"id": "e2", "source": "t1", "target": "c_second"},
        {"id": "e3", "source": "c_second", "target": "o1", "source_handle": "true"},
    ]
    errors = validate_workflow_graph(nodes, edges)
    rule_4_errors = [e for e in errors if e.rule == 4]
    assert len(rule_4_errors) == 2
    # Order matches graph_nodes declaration order (c_first appears first)
    assert rule_4_errors[0].node_id == "c_first"
    assert rule_4_errors[1].node_id == "c_second"


def test_rule_4_condition_valid_two_handles_passes() -> None:
    """Rule 4 valid case - explicit zero-error assertion (Warning #4 belt-and-suspenders).

    The parametrized fixture loop also catches this case, but an explicit
    named test makes the contract obvious in test output and survives any
    future refactor of the fixture-loop machinery.
    """
    fixture_path = (
        Path(__file__).parents[2] / "fixtures" / "graph_validation_cases.json"
    )
    cases = json.loads(fixture_path.read_text())
    case = next(c for c in cases if c["name"] == "condition_valid_two_handles")

    errors = validate_workflow_graph(
        case["input"]["graph_nodes"],
        case["input"]["graph_edges"],
    )
    rule_4_errors = [e for e in errors if e.rule == 4]
    assert rule_4_errors == [], (
        f"condition_valid_two_handles produced unexpected rule 4 errors: "
        f"{rule_4_errors}"
    )
