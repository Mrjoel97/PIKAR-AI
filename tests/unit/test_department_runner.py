"""Tests for autonomous department runner."""

import importlib
import sys
import types
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Module loader — patches Supabase so the import doesn't hit the network
# ---------------------------------------------------------------------------


def _load_department_runner_module(monkeypatch):
    """Import department_runner with stubbed Supabase dependencies."""
    fake_agents = types.ModuleType("app.agents.specialized_agents")
    for name in [
        "compliance_agent",
        "content_agent",
        "customer_support_agent",
        "data_agent",
        "financial_agent",
        "hr_agent",
        "marketing_agent",
        "operations_agent",
        "sales_agent",
        "strategic_agent",
    ]:
        setattr(fake_agents, name, SimpleNamespace(name=name))

    monkeypatch.setitem(sys.modules, "app.agents.specialized_agents", fake_agents)
    monkeypatch.setattr("app.services.supabase.get_service_client", lambda: MagicMock())
    sys.modules.pop("app.services.department_runner", None)
    return importlib.import_module("app.services.department_runner")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dept_module(monkeypatch):
    """Provide the department_runner module with stubbed dependencies."""
    return _load_department_runner_module(monkeypatch)


@pytest.fixture
def runner(dept_module):
    """Provide a DepartmentRunner instance with a mock Supabase client."""
    r = dept_module.DepartmentRunner()
    r.supabase = MagicMock()
    return r


# ---------------------------------------------------------------------------
# _should_run interval gate
# ---------------------------------------------------------------------------


class TestShouldRun:
    """Tests for the _should_run interval gate."""

    def test_returns_false_when_interval_not_elapsed(self, runner):
        """Department should be skipped if the check interval has not elapsed."""
        dept = {
            "id": "dept-1",
            "last_heartbeat": (
                datetime.now(timezone.utc) - timedelta(minutes=5)
            ).isoformat(),
            "config": {"check_interval_mins": 15},
        }
        assert runner._should_run(dept) is False

    def test_returns_true_when_interval_elapsed(self, runner):
        """Department should run if enough time has passed."""
        dept = {
            "id": "dept-2",
            "last_heartbeat": (
                datetime.now(timezone.utc) - timedelta(minutes=90)
            ).isoformat(),
            "config": {"check_interval_mins": 30},
        }
        assert runner._should_run(dept) is True

    def test_returns_true_for_invalid_timestamp(self, runner):
        """Invalid last_heartbeat should default to running."""
        dept = {
            "id": "dept-3",
            "last_heartbeat": "not-a-timestamp",
            "config": {"check_interval_mins": 30},
        }
        assert runner._should_run(dept) is True

    def test_returns_true_when_no_heartbeat(self, runner):
        """Missing last_heartbeat should always run."""
        dept = {"id": "dept-4", "config": {"check_interval_mins": 60}}
        assert runner._should_run(dept) is True

    def test_returns_true_when_interval_is_zero(self, runner):
        """Zero interval should always run."""
        dept = {
            "id": "dept-5",
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "config": {"check_interval_mins": 0},
        }
        assert runner._should_run(dept) is True

    def test_returns_true_for_invalid_interval(self, runner):
        """Non-numeric check_interval_mins should default to running."""
        dept = {
            "id": "dept-6",
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "config": {"check_interval_mins": "bad"},
        }
        assert runner._should_run(dept) is True


# ---------------------------------------------------------------------------
# _evaluate_condition
# ---------------------------------------------------------------------------


class TestEvaluateCondition:
    """Tests for trigger condition evaluation."""

    def test_metric_threshold_gte_matched(self, runner):
        """metric_threshold with gte operator should match when value >= threshold."""
        config = {"metric_key": "metrics.leads", "threshold": 10, "operator": "gte"}
        state = {"metrics": {"leads": 15}}
        matched, explanation = runner._evaluate_condition("metric_threshold", config, state)
        assert matched is True
        assert "15" in explanation

    def test_metric_threshold_gte_not_matched(self, runner):
        """metric_threshold with gte should not match when value < threshold."""
        config = {"metric_key": "metrics.leads", "threshold": 20, "operator": "gte"}
        state = {"metrics": {"leads": 5}}
        matched, _ = runner._evaluate_condition("metric_threshold", config, state)
        assert matched is False

    def test_metric_threshold_lt_operator(self, runner):
        """metric_threshold with lt operator should match when value < threshold."""
        config = {"metric_key": "score", "threshold": 50, "operator": "lt"}
        state = {"score": 30}
        matched, _ = runner._evaluate_condition("metric_threshold", config, state)
        assert matched is True

    def test_metric_threshold_eq_operator(self, runner):
        """metric_threshold with eq operator should match on equality."""
        config = {"metric_key": "level", "threshold": 3, "operator": "eq"}
        state = {"level": 3}
        matched, _ = runner._evaluate_condition("metric_threshold", config, state)
        assert matched is True

    def test_metric_threshold_missing_key(self, runner):
        """Missing metric key in state should not match."""
        config = {"metric_key": "missing.key", "threshold": 10, "operator": "gte"}
        state = {}
        matched, explanation = runner._evaluate_condition("metric_threshold", config, state)
        assert matched is False
        assert "not found" in explanation

    def test_metric_threshold_non_numeric(self, runner):
        """Non-numeric metric value should not match."""
        config = {"metric_key": "status", "threshold": 10, "operator": "gte"}
        state = {"status": "active"}
        matched, explanation = runner._evaluate_condition("metric_threshold", config, state)
        assert matched is False
        assert "Non-numeric" in explanation

    def test_time_based_enough_elapsed(self, runner):
        """time_based condition should match when enough hours have elapsed."""
        past = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
        config = {"reference_timestamp": past, "min_elapsed_hours": 5}
        matched, explanation = runner._evaluate_condition("time_based", config, {})
        assert matched is True
        assert "Elapsed" in explanation

    def test_time_based_not_enough_elapsed(self, runner):
        """time_based condition should not match when too little time has passed."""
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        config = {"reference_timestamp": recent, "min_elapsed_hours": 24}
        matched, _ = runner._evaluate_condition("time_based", config, {})
        assert matched is False

    def test_time_based_no_reference(self, runner):
        """time_based with no reference_timestamp should pass by default."""
        config = {"min_elapsed_hours": 5}
        matched, explanation = runner._evaluate_condition("time_based", config, {})
        assert matched is True
        assert "No reference timestamp" in explanation

    def test_time_based_invalid_reference(self, runner):
        """Unparseable reference_timestamp should not match."""
        config = {"reference_timestamp": "garbage", "min_elapsed_hours": 1}
        matched, explanation = runner._evaluate_condition("time_based", config, {})
        assert matched is False
        assert "Unparseable" in explanation

    def test_event_count_matched(self, runner):
        """event_count should match when count >= min_count."""
        config = {"event_key": "events.signups", "min_count": 3}
        state = {"events": {"signups": 5}}
        matched, _ = runner._evaluate_condition("event_count", config, state)
        assert matched is True

    def test_event_count_not_matched(self, runner):
        """event_count should not match when count < min_count."""
        config = {"event_key": "events.signups", "min_count": 10}
        state = {"events": {"signups": 2}}
        matched, _ = runner._evaluate_condition("event_count", config, state)
        assert matched is False

    def test_unknown_condition_type(self, runner):
        """Unknown condition_type should not match."""
        matched, explanation = runner._evaluate_condition("nonexistent_type", {}, {})
        assert matched is False
        assert "Unknown condition type" in explanation


# ---------------------------------------------------------------------------
# _core_cycle — logs no_action when nothing matches
# ---------------------------------------------------------------------------


class TestCoreCycle:
    """Tests for the shared _core_cycle logic."""

    @pytest.mark.asyncio
    async def test_core_cycle_logs_no_action_when_no_triggers(self, runner, monkeypatch):
        """When there are no triggers, workflows, or requests, no_action is logged."""
        logged_decisions = []

        async def fake_log(dept_id, decision):
            logged_decisions.append(decision)

        # Stub all three phases to return empty lists
        monkeypatch.setattr(
            runner, "_handle_inter_dept_requests", AsyncMock(return_value=[])
        )
        monkeypatch.setattr(
            runner, "_evaluate_triggers", AsyncMock(return_value=[])
        )
        monkeypatch.setattr(
            runner, "_check_workflow_completions", AsyncMock(return_value=[])
        )
        monkeypatch.setattr(runner, "_log_decision", fake_log)

        state = {"dept_id": "dept-1"}
        new_state = state.copy()
        result = await runner._core_cycle("SALES", state, new_state)

        # Should have logged a no_action decision
        assert any(d["decision_type"] == "no_action" for d in logged_decisions)
        assert "0 decisions" in result

    @pytest.mark.asyncio
    async def test_core_cycle_records_metrics(self, runner, monkeypatch):
        """Cycle metrics should be recorded in new_state."""
        monkeypatch.setattr(
            runner, "_handle_inter_dept_requests", AsyncMock(return_value=[])
        )
        monkeypatch.setattr(
            runner,
            "_evaluate_triggers",
            AsyncMock(
                return_value=[
                    {"decision_type": "workflow_launched"},
                    {"decision_type": "trigger_matched"},
                ]
            ),
        )
        monkeypatch.setattr(
            runner,
            "_check_workflow_completions",
            AsyncMock(
                return_value=[{"decision_type": "workflow_completed"}]
            ),
        )
        monkeypatch.setattr(runner, "_log_decision", AsyncMock())

        state = {"dept_id": "dept-1"}
        new_state = state.copy()
        await runner._core_cycle("SALES", state, new_state)

        metrics = new_state["last_cycle_metrics"]
        assert metrics["workflows_launched"] == 1
        assert metrics["workflows_completed"] == 1
        assert "timestamp" in metrics


# ---------------------------------------------------------------------------
# Trigger cooldown
# ---------------------------------------------------------------------------


class TestTriggerCooldown:
    """Tests for trigger cooldown enforcement."""

    @pytest.mark.asyncio
    async def test_trigger_cooldown_respected(self, runner, monkeypatch):
        """A trigger with recent last_triggered_at should be skipped."""
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        triggers = [
            {
                "id": "t-1",
                "name": "recent_trigger",
                "enabled": True,
                "cooldown_hours": 24,
                "last_triggered_at": recent,
                "condition_type": "metric_threshold",
                "condition_config": {
                    "metric_key": "score",
                    "threshold": 0,
                    "operator": "gte",
                },
            }
        ]

        async def fake_execute(query_builder, op_name=""):
            return SimpleNamespace(data=triggers)

        monkeypatch.setattr(
            "app.services.department_runner.execute_async", fake_execute
        )

        state = {}
        new_state = {}
        decisions = await runner._evaluate_triggers("dept-1", "SALES", state, new_state)

        assert len(decisions) == 1
        assert decisions[0]["decision_type"] == "trigger_skipped"
        assert decisions[0]["outcome"] == "cooldown"

    @pytest.mark.asyncio
    async def test_trigger_fires_after_cooldown_expires(self, runner, monkeypatch):
        """A trigger whose cooldown has expired should fire."""
        old = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        triggers = [
            {
                "id": "t-2",
                "name": "expired_cooldown",
                "enabled": True,
                "cooldown_hours": 24,
                "last_triggered_at": old,
                "condition_type": "metric_threshold",
                "condition_config": {
                    "metric_key": "score",
                    "threshold": 0,
                    "operator": "gte",
                },
                "action_type": "notify",
                "action_config": {"message": "hello"},
                "department_id": "dept-1",
            }
        ]

        call_log = []

        async def fake_execute(query_builder, op_name=""):
            call_log.append(op_name)
            return SimpleNamespace(data=triggers)

        monkeypatch.setattr(
            "app.services.department_runner.execute_async", fake_execute
        )

        state = {"score": 1}
        new_state = {}
        decisions = await runner._evaluate_triggers("dept-1", "SALES", state, new_state)

        types = [d["decision_type"] for d in decisions]
        assert "notification_sent" in types
        assert "trigger_matched" in types


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Tests for per-cycle workflow rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_caps_workflows(self, runner, monkeypatch):
        """After MAX_WORKFLOWS_PER_CYCLE, further triggers should be rate-limited."""
        # STRATEGIC has max 1 workflow per cycle
        triggers = [
            {
                "id": f"t-{i}",
                "name": f"trigger_{i}",
                "enabled": True,
                "cooldown_hours": 0,
                "last_triggered_at": None,
                "condition_type": "metric_threshold",
                "condition_config": {
                    "metric_key": "score",
                    "threshold": 0,
                    "operator": "gte",
                },
                "action_type": "launch_workflow",
                "action_config": {
                    "template_id": f"tmpl-{i}",
                    "user_id": "user-1",
                },
                "department_id": "dept-1",
            }
            for i in range(3)  # 3 triggers, but STRATEGIC allows only 1
        ]

        wf_counter = [0]

        async def fake_execute(query_builder, op_name=""):
            if "get_triggers" in op_name:
                return SimpleNamespace(data=triggers)
            if "launch_workflow" in op_name:
                wf_counter[0] += 1
                return SimpleNamespace(data=[{"id": f"wf-{wf_counter[0]}"}])
            return SimpleNamespace(data=[])

        monkeypatch.setattr(
            "app.services.department_runner.execute_async", fake_execute
        )

        state = {"score": 10}
        new_state = {}
        decisions = await runner._evaluate_triggers(
            "dept-1", "STRATEGIC", state, new_state
        )

        # Should have launched exactly 1 workflow (STRATEGIC max)
        launched = [d for d in decisions if d["decision_type"] == "workflow_launched"]
        rate_limited = [
            d
            for d in decisions
            if d["decision_type"] == "trigger_skipped"
            and d.get("outcome") == "rate_limited"
        ]
        assert len(launched) == 1
        assert len(rate_limited) >= 1  # remaining triggers were rate-limited


# ---------------------------------------------------------------------------
# Workflow completion tracking
# ---------------------------------------------------------------------------


class TestWorkflowCompletions:
    """Tests for pending workflow status reconciliation."""

    @pytest.mark.asyncio
    async def test_completed_workflow_removed_from_pending(self, runner, monkeypatch):
        """A completed workflow should be removed from pending_workflows."""
        state = {
            "pending_workflows": [
                {
                    "workflow_execution_id": "wf-1",
                    "trigger_id": "t-1",
                    "launched_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        new_state = {}

        async def fake_execute(query_builder, op_name=""):
            return SimpleNamespace(
                data=[{"id": "wf-1", "status": "completed", "context": {}}]
            )

        monkeypatch.setattr(
            "app.services.department_runner.execute_async", fake_execute
        )

        decisions = await runner._check_workflow_completions(state, new_state)

        assert len(decisions) == 1
        assert decisions[0]["decision_type"] == "workflow_completed"
        # The completed workflow should be removed from pending
        assert new_state["pending_workflows"] == []

    @pytest.mark.asyncio
    async def test_running_workflow_stays_pending(self, runner, monkeypatch):
        """A still-running workflow should remain in pending_workflows."""
        state = {
            "pending_workflows": [
                {
                    "workflow_execution_id": "wf-2",
                    "trigger_id": "t-2",
                    "launched_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        new_state = {}

        async def fake_execute(query_builder, op_name=""):
            return SimpleNamespace(
                data=[{"id": "wf-2", "status": "running", "context": {}}]
            )

        monkeypatch.setattr(
            "app.services.department_runner.execute_async", fake_execute
        )

        decisions = await runner._check_workflow_completions(state, new_state)

        assert len(decisions) == 0
        assert len(new_state["pending_workflows"]) == 1

    @pytest.mark.asyncio
    async def test_missing_workflow_removed_from_pending(self, runner, monkeypatch):
        """A deleted workflow should be dropped from pending with a 'missing' decision."""
        state = {
            "pending_workflows": [
                {
                    "workflow_execution_id": "wf-gone",
                    "trigger_id": "t-3",
                    "launched_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        new_state = {}

        async def fake_execute(query_builder, op_name=""):
            return SimpleNamespace(data=[])

        monkeypatch.setattr(
            "app.services.department_runner.execute_async", fake_execute
        )

        decisions = await runner._check_workflow_completions(state, new_state)

        assert len(decisions) == 1
        assert decisions[0]["decision_type"] == "workflow_missing"
        assert new_state["pending_workflows"] == []

    @pytest.mark.asyncio
    async def test_failed_workflow_removed_from_pending(self, runner, monkeypatch):
        """A failed workflow should be removed from pending with a 'failed' decision."""
        state = {
            "pending_workflows": [
                {
                    "workflow_execution_id": "wf-fail",
                    "trigger_id": "t-4",
                    "launched_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        new_state = {}

        async def fake_execute(query_builder, op_name=""):
            return SimpleNamespace(
                data=[{"id": "wf-fail", "status": "failed", "context": {}}]
            )

        monkeypatch.setattr(
            "app.services.department_runner.execute_async", fake_execute
        )

        decisions = await runner._check_workflow_completions(state, new_state)

        assert len(decisions) == 1
        assert decisions[0]["decision_type"] == "workflow_failed"
        assert decisions[0]["outcome"] == "failed"
        assert new_state["pending_workflows"] == []

    @pytest.mark.asyncio
    async def test_no_pending_workflows_returns_empty(self, runner, monkeypatch):
        """When there are no pending workflows, return empty decisions."""
        state = {}
        new_state = {}
        decisions = await runner._check_workflow_completions(state, new_state)
        assert decisions == []

    @pytest.mark.asyncio
    async def test_completed_workflow_updates_initiative(self, runner, monkeypatch):
        """Completed workflow with an initiative_id should update the initiative."""
        state = {
            "pending_workflows": [
                {
                    "workflow_execution_id": "wf-init",
                    "trigger_id": "t-5",
                    "launched_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        new_state = {}
        update_calls = []

        async def fake_execute(query_builder, op_name=""):
            if "check_wf_status" in op_name:
                return SimpleNamespace(
                    data=[
                        {
                            "id": "wf-init",
                            "status": "completed",
                            "context": {"initiative_id": "init-42"},
                        }
                    ]
                )
            if "update_initiative" in op_name:
                update_calls.append(op_name)
                return SimpleNamespace(data=[])
            return SimpleNamespace(data=[])

        monkeypatch.setattr(
            "app.services.department_runner.execute_async", fake_execute
        )

        decisions = await runner._check_workflow_completions(state, new_state)

        assert len(decisions) == 1
        assert decisions[0]["action_taken"]["initiative_id"] == "init-42"
        assert len(update_calls) == 1


# ---------------------------------------------------------------------------
# Inter-department requests
# ---------------------------------------------------------------------------


class TestInterDeptRequests:
    """Tests for inter-department request handling."""

    @pytest.mark.asyncio
    async def test_acknowledges_pending_requests(self, runner, monkeypatch):
        """Pending inter-dept requests should be acknowledged."""
        requests = [
            {
                "id": "req-1",
                "from_department_id": "dept-sales",
                "to_department_id": "dept-marketing",
                "request_type": "content_request",
                "status": "pending",
            }
        ]

        async def fake_execute(query_builder, op_name=""):
            if "get_inter_dept_pending" in op_name:
                return SimpleNamespace(data=requests)
            return SimpleNamespace(data=[])

        monkeypatch.setattr(
            "app.services.department_runner.execute_async", fake_execute
        )

        decisions = await runner._handle_inter_dept_requests("dept-marketing")

        assert len(decisions) == 1
        assert decisions[0]["decision_type"] == "inter_dept_acknowledged"
        assert decisions[0]["action_taken"]["request_id"] == "req-1"

    @pytest.mark.asyncio
    async def test_no_dept_id_returns_empty(self, runner):
        """None dept_id should return empty list without DB calls."""
        decisions = await runner._handle_inter_dept_requests(None)
        assert decisions == []


# ---------------------------------------------------------------------------
# Trigger action executor
# ---------------------------------------------------------------------------


class TestTriggerActionExecutor:
    """Tests for _execute_trigger_action."""

    @pytest.mark.asyncio
    async def test_launch_workflow_action(self, runner, monkeypatch):
        """launch_workflow action should create a workflow execution entry."""
        trigger = {
            "id": "t-wf",
            "name": "auto_wf",
            "department_id": "dept-1",
            "action_type": "launch_workflow",
            "action_config": {
                "template_id": "tmpl-1",
                "workflow_name": "Auto Test",
                "user_id": "user-1",
            },
        }

        async def fake_execute(query_builder, op_name=""):
            return SimpleNamespace(data=[{"id": "wf-new"}])

        monkeypatch.setattr(
            "app.services.department_runner.execute_async", fake_execute
        )

        new_state = {}
        decisions, launched = await runner._execute_trigger_action(trigger, new_state)

        assert launched == 1
        assert any(d["decision_type"] == "workflow_launched" for d in decisions)
        assert len(new_state["pending_workflows"]) == 1

    @pytest.mark.asyncio
    async def test_launch_workflow_missing_template(self, runner, monkeypatch):
        """launch_workflow without template_id should produce an error decision."""
        trigger = {
            "id": "t-bad",
            "name": "no_template",
            "department_id": "dept-1",
            "action_type": "launch_workflow",
            "action_config": {},
        }

        new_state = {}
        decisions, launched = await runner._execute_trigger_action(trigger, new_state)

        assert launched == 0
        assert any(d["decision_type"] == "trigger_error" for d in decisions)

    @pytest.mark.asyncio
    async def test_escalate_action(self, runner, monkeypatch):
        """escalate action should create an inter-dept request."""
        trigger = {
            "id": "t-esc",
            "name": "escalation",
            "department_id": "dept-sales",
            "action_type": "escalate",
            "action_config": {
                "target_department_id": "dept-support",
                "request_type": "urgent_issue",
            },
        }

        async def fake_execute(query_builder, op_name=""):
            return SimpleNamespace(data=[])

        monkeypatch.setattr(
            "app.services.department_runner.execute_async", fake_execute
        )

        new_state = {}
        decisions, launched = await runner._execute_trigger_action(trigger, new_state)

        assert launched == 0
        assert any(d["decision_type"] == "escalated" for d in decisions)

    @pytest.mark.asyncio
    async def test_notify_action(self, runner, monkeypatch):
        """notify action should produce a notification_sent decision."""
        trigger = {
            "id": "t-notify",
            "name": "alert",
            "department_id": "dept-1",
            "action_type": "notify",
            "action_config": {"message": "Test alert", "severity": "warning"},
        }

        new_state = {}
        decisions, launched = await runner._execute_trigger_action(trigger, new_state)

        assert launched == 0
        assert len(decisions) == 1
        assert decisions[0]["decision_type"] == "notification_sent"
        assert decisions[0]["action_taken"]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_unknown_action_type(self, runner, monkeypatch):
        """Unknown action_type should produce an error decision."""
        trigger = {
            "id": "t-unk",
            "name": "mystery",
            "department_id": "dept-1",
            "action_type": "teleport",
            "action_config": {},
        }

        new_state = {}
        decisions, launched = await runner._execute_trigger_action(trigger, new_state)

        assert launched == 0
        assert any(d["decision_type"] == "trigger_error" for d in decisions)
        assert "Unknown action_type" in decisions[0]["decision_logic"]
