import pytest

from app.workflows.engine import WorkflowEngine


class _Resp:
    """Awaitable response for double-await patterns."""

    def __init__(self, data):
        self.data = data

    def __await__(self):
        return self._identity().__await__()

    async def _identity(self):
        return self


class _Table:
    def __init__(self, name: str, db: "_Db"):
        self._name = name
        self._db = db

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    async def execute(self):
        if self._name == "workflow_executions":
            return _Resp([self._db.execution])
        if self._name == "workflow_steps":
            return _Resp(self._db.steps)
        raise AssertionError(f"Unexpected table {self._name}")


class _Db:
    def __init__(self, execution, steps):
        self.execution = execution
        self.steps = steps

    def table(self, name: str):
        return _Table(name, self)


@pytest.mark.asyncio
async def test_get_execution_status_surfaces_trust_summary_and_evidence():
    execution = {
        "id": "exec-1",
        "user_id": "u1",
        "current_phase_index": 0,
        "current_step_index": 0,
        "status": "running",
        "workflow_templates": {
            "name": "Idea-to-Venture",
            "phases": [
                {
                    "name": "Plan",
                    "steps": [
                        {
                            "name": "Create task",
                            "tool": "create_task",
                            "required_approval": False,
                        }
                    ],
                }
            ],
        },
    }
    steps = [
        {
            "id": "step-1",
            "execution_id": "exec-1",
            "phase_name": "Plan",
            "step_name": "Create task",
            "status": "completed",
            "input_data": {"description": "Do work"},
            "output_data": {
                "success": True,
                "task_id": "task-1",
                "task": {"id": "task-1"},
                "_execution_meta": {
                    "tool_name": "create_task",
                    "trust_class": "real",
                    "verification_status": "verified",
                    "evidence_refs": [{"type": "task", "value": "task-1"}],
                },
            },
            "error_message": None,
            "started_at": "2026-03-07T10:00:00Z",
            "completed_at": "2026-03-07T10:01:00Z",
            "created_at": "2026-03-07T10:00:00Z",
            "updated_at": "2026-03-07T10:01:00Z",
            "phase_index": 0,
            "step_index": 0,
            "attempt_count": 1,
            "phase_key": "plan",
        }
    ]
    engine = object.__new__(WorkflowEngine)
    engine._async_client = _Db(execution, steps)

    result = await engine.get_execution_status("exec-1")

    assert result["history"][0]["tool_name"] == "create_task"
    assert result["history"][0]["trust_class"] == "real"
    assert result["history"][0]["verification_status"] == "verified"
    assert result["trust_summary"]["trust_counts"]["real"] == 1
    assert result["verification_status"] == "verified"
    assert result["evidence_refs"][0]["value"] == "task-1"


@pytest.mark.asyncio
async def test_get_execution_status_marks_human_gated_steps_as_pending():
    execution = {
        "id": "exec-2",
        "user_id": "u1",
        "current_phase_index": 0,
        "current_step_index": 0,
        "status": "waiting_approval",
        "workflow_templates": {
            "name": "Landing Page to Launch",
            "phases": [
                {
                    "name": "Launch",
                    "steps": [
                        {
                            "name": "Publish page",
                            "tool": "publish_page",
                            "required_approval": True,
                            "risk_level": "publish",
                        }
                    ],
                }
            ],
        },
    }
    steps = [
        {
            "id": "step-2",
            "execution_id": "exec-2",
            "phase_name": "Launch",
            "step_name": "Publish page",
            "status": "waiting_approval",
            "input_data": {"page_id": "page-1"},
            "output_data": {},
            "error_message": None,
            "started_at": "2026-03-07T10:00:00Z",
            "completed_at": None,
            "created_at": "2026-03-07T10:00:00Z",
            "updated_at": "2026-03-07T10:00:00Z",
            "phase_index": 0,
            "step_index": 0,
            "attempt_count": 1,
            "phase_key": "launch",
        }
    ]
    engine = object.__new__(WorkflowEngine)
    engine._async_client = _Db(execution, steps)

    result = await engine.get_execution_status("exec-2")

    assert result["history"][0]["trust_class"] == "human_gated"
    assert result["approval_state"] == "pending"
    assert result["verification_status"] == "pending"