import importlib
import sys
import types
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock


def _load_department_runner_module(monkeypatch):
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


def test_should_run_returns_false_when_interval_not_elapsed(monkeypatch):
    module = _load_department_runner_module(monkeypatch)
    runner = module.DepartmentRunner()
    dept = {
        "id": "dept-1",
        "last_heartbeat": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        "config": {"check_interval_mins": 15},
    }

    assert runner._should_run(dept) is False


def test_should_run_returns_true_when_interval_elapsed(monkeypatch):
    module = _load_department_runner_module(monkeypatch)
    runner = module.DepartmentRunner()
    dept = {
        "id": "dept-2",
        "last_heartbeat": (datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat(),
        "config": {"check_interval_mins": 30},
    }

    assert runner._should_run(dept) is True


def test_should_run_returns_true_for_invalid_timestamp(monkeypatch):
    module = _load_department_runner_module(monkeypatch)
    runner = module.DepartmentRunner()
    dept = {
        "id": "dept-3",
        "last_heartbeat": "not-a-timestamp",
        "config": {"check_interval_mins": 30},
    }

    assert runner._should_run(dept) is True
