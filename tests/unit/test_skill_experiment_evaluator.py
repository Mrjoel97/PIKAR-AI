# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for SkillExperimentEvaluator decision logic.

Tests cover:
- Pure helpers (_interaction_quality, _two_proportion_z, _duration_expired)
- _evaluate_one decision branches:
    * below_min_samples -> running
    * significant_lift -> promoted
    * significant_regression -> reverted
    * inconclusive_low_traffic (duration expired) -> inconclusive_reverted
    * inconclusive_max_samples -> inconclusive_reverted
    * no_decision_yet -> running

Apply paths (_apply_promote / _apply_revert) are stubbed; their DB orchestration
is intentionally not unit-tested.  The aim is to lock the math + decision
flow so regressions to those branches show up here loudly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.services.skill_experiment_evaluator import (
    SkillExperimentEvaluator,
    _duration_expired,
    _interaction_quality,
    _safe_rate,
    _two_proportion_z,
)

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "task_completed, user_feedback, expected",
    [
        (True, "positive", 1),
        (True, "neutral", 1),
        (True, None, 1),
        (True, "negative", 0),  # negative overrides completion
        (False, "positive", 1),  # explicit positive overrides incompletion
        (False, "negative", 0),
        (False, None, 0),
        (None, None, 0),
        (None, "positive", 1),
    ],
)
def test_interaction_quality(task_completed, user_feedback, expected):
    assert _interaction_quality(task_completed, user_feedback) == expected


def test_safe_rate_handles_zero_denominator():
    assert _safe_rate(0, 0) == 0.0
    assert _safe_rate(5, 0) == 0.0
    assert _safe_rate(5, 10) == 0.5


def test_two_proportion_z_significant_lift():
    # Big lift, big samples: should be solidly positive z.
    z = _two_proportion_z(q_c=30, n_c=100, q_t=70, n_t=100)
    assert z is not None
    assert z > 5.0  # 40-point lift on n=100 each => clearly significant


def test_two_proportion_z_significant_regression():
    z = _two_proportion_z(q_c=70, n_c=100, q_t=30, n_t=100)
    assert z is not None
    assert z < -5.0


def test_two_proportion_z_no_difference():
    z = _two_proportion_z(q_c=50, n_c=100, q_t=50, n_t=100)
    assert z is not None
    assert abs(z) < 0.5


def test_two_proportion_z_empty_arm():
    assert _two_proportion_z(0, 0, 5, 10) is None
    assert _two_proportion_z(5, 10, 0, 0) is None


def test_two_proportion_z_no_variance():
    # All zeros: pooled p == 0 => can't test.
    assert _two_proportion_z(0, 50, 0, 50) is None
    # All ones: pooled p == 1 => can't test.
    assert _two_proportion_z(50, 50, 50, 50) is None


def test_duration_expired_iso_string():
    long_ago = (datetime.now(tz=timezone.utc) - timedelta(days=20)).isoformat()
    assert _duration_expired(long_ago, max_duration_days=14) is True


def test_duration_expired_recent():
    recent = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
    assert _duration_expired(recent, max_duration_days=14) is False


def test_duration_expired_none():
    assert _duration_expired(None, max_duration_days=14) is False


# ---------------------------------------------------------------------------
# _evaluate_one decision branches
# ---------------------------------------------------------------------------


class _StubEvaluator(SkillExperimentEvaluator):
    """SkillExperimentEvaluator with the supabase client + DB mutations stubbed.

    Tests inject ``_arms`` to control what _aggregate_arms returns and assert
    on the outcome string from _evaluate_one.
    """

    def __init__(self, arms: dict[str, tuple[int, int]]) -> None:
        # Skip the real __init__ — we don't need a real Supabase client.
        self.client = MagicMock()
        self._arms = arms
        self.applied: list[tuple[str, dict[str, Any]]] = []

    async def _aggregate_arms(self, exp_id: str):
        return self._arms

    async def _apply_promote(self, exp, decision):
        decision["outcome"] = "promoted"
        self.applied.append(("promote", decision))
        return decision

    async def _apply_revert(self, exp, decision, *, inconclusive):
        decision["outcome"] = (
            "inconclusive_reverted" if inconclusive else "reverted"
        )
        self.applied.append(
            ("revert" if not inconclusive else "inconclusive_revert", decision)
        )
        return decision


def _exp(
    *,
    started_at: str | None = None,
    min_samples: int = 50,
    max_samples: int = 500,
    max_duration_days: int = 14,
    min_effect_size: float = 0.05,
) -> dict[str, Any]:
    return {
        "id": "exp-1",
        "skill_name": "test_skill",
        "control_version_id": "ver-c",
        "candidate_version_id": "ver-t",
        "source_action_id": "act-1",
        "min_samples_per_arm": min_samples,
        "max_samples_per_arm": max_samples,
        "max_duration_days": max_duration_days,
        "alpha": 0.05,
        "min_effect_size": min_effect_size,
        "started_at": started_at
        or (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat(),
        "metadata": {},
    }


@pytest.mark.asyncio
async def test_below_min_samples_keeps_running():
    """One arm under the minimum sample size -> running (no decision)."""
    ev = _StubEvaluator(arms={"control": (10, 5), "treatment": (10, 6)})
    result = await ev._evaluate_one(_exp())
    assert result["outcome"] == "running"
    assert result["decision_reason"] == "below_min_samples"
    assert ev.applied == []


@pytest.mark.asyncio
async def test_significant_lift_promotes():
    """Treatment significantly better AND beats min_effect_size -> promote."""
    ev = _StubEvaluator(arms={"control": (50, 25), "treatment": (50, 45)})
    result = await ev._evaluate_one(_exp())
    assert result["outcome"] == "promoted"
    assert result["decision_reason"] == "significant_lift"
    assert ev.applied[0][0] == "promote"


@pytest.mark.asyncio
async def test_significant_regression_reverts():
    """Treatment significantly worse -> revert regardless of effect size."""
    ev = _StubEvaluator(arms={"control": (50, 45), "treatment": (50, 25)})
    result = await ev._evaluate_one(_exp())
    assert result["outcome"] == "reverted"
    assert result["decision_reason"] == "significant_regression"


@pytest.mark.asyncio
async def test_significant_lift_below_effect_size_keeps_running():
    """Lift is statistically significant but tiny -> continue."""
    # Very large n with small absolute lift: z is high, p_diff is tiny.
    ev = _StubEvaluator(
        arms={"control": (10000, 5000), "treatment": (10000, 5100)}
    )
    result = await ev._evaluate_one(
        _exp(min_samples=50, max_samples=20000, min_effect_size=0.05)
    )
    # p_t - p_c = 0.01, below min_effect_size of 0.05, so don't promote.
    # Within sample budget, so keep running.
    assert result["outcome"] == "running"
    assert result["decision_reason"] == "no_decision_yet"


@pytest.mark.asyncio
async def test_max_duration_exceeded_triggers_inconclusive_revert():
    """Duration expired without verdict -> inconclusive revert."""
    long_ago = (
        datetime.now(tz=timezone.utc) - timedelta(days=30)
    ).isoformat()
    ev = _StubEvaluator(arms={"control": (60, 30), "treatment": (60, 32)})
    result = await ev._evaluate_one(
        _exp(started_at=long_ago, max_duration_days=14)
    )
    assert result["outcome"] == "inconclusive_reverted"
    assert result["decision_reason"] == "inconclusive_low_traffic"


@pytest.mark.asyncio
async def test_sample_budget_exhausted_triggers_inconclusive_revert():
    """Both arms hit max_samples_per_arm without significance -> inconclusive revert."""
    ev = _StubEvaluator(
        arms={"control": (500, 250), "treatment": (500, 255)}
    )
    result = await ev._evaluate_one(_exp(max_samples=500))
    assert result["outcome"] == "inconclusive_reverted"
    assert result["decision_reason"] == "inconclusive_max_samples"


@pytest.mark.asyncio
async def test_empty_treatment_returns_no_signal():
    """Treatment arm empty and duration not expired -> running with no_signal_yet."""
    ev = _StubEvaluator(arms={"control": (60, 30), "treatment": (0, 0)})
    # min_samples=50 means the empty treatment arm trips below_min_samples first.
    result = await ev._evaluate_one(_exp(min_samples=50))
    assert result["outcome"] == "running"
    # The below_min_samples branch fires before we ever try the z-test.
    assert result["decision_reason"] == "below_min_samples"


@pytest.mark.asyncio
async def test_empty_treatment_with_duration_expired_is_inconclusive():
    """Empty treatment + duration expired -> inconclusive_no_signal -> revert."""
    long_ago = (
        datetime.now(tz=timezone.utc) - timedelta(days=30)
    ).isoformat()
    ev = _StubEvaluator(arms={"control": (60, 30), "treatment": (0, 0)})
    # Lower min_samples so we skip the below_min_samples gate and hit the
    # z-test path with no signal.
    result = await ev._evaluate_one(
        _exp(started_at=long_ago, min_samples=0)
    )
    assert result["outcome"] == "inconclusive_reverted"
    assert result["decision_reason"] == "inconclusive_no_signal"
