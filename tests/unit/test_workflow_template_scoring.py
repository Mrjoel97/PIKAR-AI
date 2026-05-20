# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for workflow_template_scoring pure helpers.

Locks the math:
- _compute_metrics: rate computation against synthetic runs + steps
- _composite: weights sum to 1.0 and weight rationale is preserved
- _trend: improving / declining / stable / new
"""

from __future__ import annotations

import pytest

from app.services.workflow_template_scoring import (
    _W_COMPLETION,
    _W_ERROR,
    _W_ESCALATION,
    _W_RETRY,
    _composite,
    _compute_metrics,
    _trend,
)


def test_weights_sum_to_one():
    assert (
        pytest.approx(_W_COMPLETION + _W_ERROR + _W_RETRY + _W_ESCALATION) == 1.0
    )


def test_compute_metrics_basic():
    runs = [
        {"id": "r1", "user_id": "u1", "status": "completed"},
        {"id": "r2", "user_id": "u2", "status": "failed"},
        {"id": "r3", "user_id": "u1", "status": "running"},
        {"id": "r4", "user_id": "u3", "status": "completed"},
    ]
    steps_by_exec = {
        "r1": [{"attempt_count": 1, "sla_status": "on_time"}],
        "r2": [{"attempt_count": 3, "sla_status": "escalated"}],
        "r3": [{"attempt_count": 1, "sla_status": "escalated"}],
        # r4 has no steps recorded.
    }
    m = _compute_metrics(runs, steps_by_exec)
    assert m["total"] == 4
    assert m["unique_users"] == 3
    assert m["completion_rate"] == 0.5  # 2/4
    assert m["error_rate"] == 0.25  # 1/4
    assert m["retry_rate"] == 0.25  # only r2 had attempt_count > 1
    assert m["escalation_rate"] == 0.5  # r2 + r3


def test_compute_metrics_empty_runs():
    m = _compute_metrics([], {})
    assert m["total"] == 0
    assert m["completion_rate"] == 0.0
    assert m["error_rate"] == 0.0
    assert m["retry_rate"] == 0.0
    assert m["escalation_rate"] == 0.0
    assert m["unique_users"] == 0


def test_composite_perfect_run():
    """All-completed, no errors / retries / escalations -> max score."""
    m = {
        "completion_rate": 1.0,
        "error_rate": 0.0,
        "retry_rate": 0.0,
        "escalation_rate": 0.0,
    }
    # 0.5*1 + 0.2*1 + 0.15*1 + 0.15*1 = 1.0
    assert _composite(m) == pytest.approx(1.0)


def test_composite_worst_case():
    """All-failed, all-retried, all-escalated, no completion -> 0."""
    m = {
        "completion_rate": 0.0,
        "error_rate": 1.0,
        "retry_rate": 1.0,
        "escalation_rate": 1.0,
    }
    assert _composite(m) == pytest.approx(0.0)


def test_composite_partial_signals():
    """Half completion, no errors, some retries: predictable composite."""
    m = {
        "completion_rate": 0.5,
        "error_rate": 0.0,
        "retry_rate": 0.2,
        "escalation_rate": 0.1,
    }
    # 0.5*0.5 + 0.2*1.0 + 0.15*0.8 + 0.15*0.9
    expected = 0.5 * 0.5 + 0.2 * 1.0 + 0.15 * 0.8 + 0.15 * 0.9
    assert _composite(m) == pytest.approx(expected)


def test_trend_new_when_no_previous():
    delta, trend = _trend(0.5, None)
    assert delta is None
    assert trend == "new"


def test_trend_improving():
    delta, trend = _trend(0.60, 0.50)
    assert delta == pytest.approx(0.10)
    assert trend == "improving"


def test_trend_declining():
    delta, trend = _trend(0.40, 0.50)
    assert delta == pytest.approx(-0.10)
    assert trend == "declining"


def test_trend_stable_within_epsilon():
    delta, trend = _trend(0.501, 0.500)
    assert trend == "stable"
    assert abs(delta) < 0.02


def test_retry_rate_ignores_steps_without_attempt_count():
    """attempt_count == None should not falsely count as a retry."""
    runs = [{"id": "r1", "user_id": "u1", "status": "completed"}]
    steps_by_exec = {
        "r1": [{"attempt_count": None, "sla_status": None}],
    }
    m = _compute_metrics(runs, steps_by_exec)
    assert m["retry_rate"] == 0.0
    assert m["escalation_rate"] == 0.0
