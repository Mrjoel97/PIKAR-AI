from app.workflows import readiness


class _StubQuery:
    def __init__(self, rows=None, error=None):
        self._rows = rows
        self._error = error

    def select(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self._error:
            raise RuntimeError(self._error)

        class _Resp:
            pass

        resp = _Resp()
        resp.data = self._rows or []
        return resp


class _StubClient:
    def __init__(self, template_rows, readiness_rows=None, readiness_error=None):
        self._template_rows = template_rows
        self._readiness_rows = readiness_rows or []
        self._readiness_error = readiness_error

    def table(self, name):
        if name == "workflow_templates":
            return _StubQuery(self._template_rows)
        if name == "workflow_readiness":
            return _StubQuery(self._readiness_rows, self._readiness_error)
        raise AssertionError(f"Unexpected table name: {name}")


def _fake_tool(name: str, module: str, with_schema: bool = True):
    async def _tool(**_kwargs):
        return {"status": "ok"}

    _tool.__name__ = name
    _tool.__module__ = module
    if with_schema:
        class _Schema:
            model_fields = {"query": object()}
        _tool.input_schema = _Schema
    return _tool


def _strict_step(tool: str, *, required_approval: bool = False, risk_level: str = "medium"):
    return {
        "name": "S1",
        "tool": tool,
        "required_approval": required_approval,
        "input_bindings": {"query": {"value": "market"}},
        "risk_level": risk_level,
        "required_integrations": ["crm"] if risk_level == "publish" else [],
        "verification_checks": ["success"],
        "expected_outputs": ["results"],
        "allow_parallel": False,
    }


def test_build_workflow_readiness_report_classifies_workflows(monkeypatch):
    templates = [
        {
            "id": "t1",
            "name": "Direct Workflow",
            "lifecycle_status": "published",
            "phases": [{"name": "P1", "steps": [_strict_step("direct_tool")]}],
        },
        {
            "id": "t2",
            "name": "Approval Workflow",
            "lifecycle_status": "published",
            "phases": [{"name": "P1", "steps": [_strict_step("direct_tool", required_approval=True, risk_level="publish")]}],
        },
        {
            "id": "t3",
            "name": "Integration Workflow",
            "lifecycle_status": "published",
            "phases": [{"name": "P1", "steps": [_strict_step("integration_tool")]}],
        },
        {
            "id": "t4",
            "name": "Degraded Workflow",
            "lifecycle_status": "published",
            "phases": [{"name": "P1", "steps": [_strict_step("degraded_tool")]}],
        },
    ]
    readiness_rows = [
        {"template_id": "t1", "status": "ready", "required_integrations": []},
        {"template_id": "t2", "status": "ready", "required_integrations": ["cms"]},
        {"template_id": "t3", "status": "ready", "required_integrations": ["email"]},
        {"template_id": "t4", "status": "ready", "required_integrations": []},
    ]

    monkeypatch.setattr(readiness, "get_service_client", lambda: _StubClient(templates, readiness_rows))
    monkeypatch.setattr(
        readiness,
        "TOOL_REGISTRY",
        {
            "direct_tool": _fake_tool("direct_tool", "app.agents.tools.content.tools"),
            "integration_tool": _fake_tool("integrated_run", "app.agents.tools.integration_tools"),
            "degraded_tool": _fake_tool("degraded_run", "app.agents.tools.degraded_tools"),
        },
    )

    monkeypatch.setenv("WORKFLOW_STRICT_TOOL_RESOLUTION", "true")
    monkeypatch.setenv("WORKFLOW_STRICT_CRITICAL_TOOL_GUARD", "true")
    monkeypatch.setenv("WORKFLOW_ALLOW_FALLBACK_SIMULATION", "false")
    monkeypatch.setenv("WORKFLOW_ENFORCE_READINESS_GATE", "true")
    monkeypatch.setenv("BACKEND_API_URL", "https://api.example.com")
    monkeypatch.setenv("WORKFLOW_SERVICE_SECRET", "x" * 40)

    report = readiness.build_workflow_readiness_report()

    assert report["summary"]["templates_total"] == 4
    assert report["workflow_labels"]["fully autonomous"] == 1
    assert report["workflow_labels"]["human-gated"] == 1
    assert report["workflow_labels"]["integration-dependent"] == 1
    assert report["workflow_labels"]["degraded-simulation-prone"] == 1
    assert report["checks"]["strict_tool_resolution_enabled"] is True
    assert report["checks"]["fallback_simulation_disabled"] is True
    assert report["checks"]["readiness_gate_enabled"] is True
    assert report["checks"]["all_templates_have_readiness_rows"] is True
    assert report["checks"]["integration_workflows_have_required_integrations_metadata"] is True


def test_build_workflow_readiness_report_detects_missing_tools(monkeypatch):
    templates = [
        {
            "id": "t1",
            "name": "Missing Tool Workflow",
            "lifecycle_status": "published",
            "phases": [{"name": "P1", "steps": [_strict_step("missing_tool")]}],
        }
    ]

    monkeypatch.setattr(readiness, "get_service_client", lambda: _StubClient(templates))
    monkeypatch.setattr(readiness, "TOOL_REGISTRY", {})
    monkeypatch.setenv("WORKFLOW_STRICT_TOOL_RESOLUTION", "false")
    monkeypatch.setenv("WORKFLOW_ALLOW_FALLBACK_SIMULATION", "true")
    monkeypatch.setenv("WORKFLOW_ENFORCE_READINESS_GATE", "false")
    monkeypatch.delenv("BACKEND_API_URL", raising=False)
    monkeypatch.delenv("WORKFLOW_SERVICE_SECRET", raising=False)

    report = readiness.build_workflow_readiness_report()

    assert report["status"] == "not_ready"
    assert "missing_tool" in report["unknown_tool_workflows"]
    assert "no_unknown_tools_in_templates" in report["failing_checks"]


def test_build_workflow_readiness_report_handles_missing_readiness_table(monkeypatch):
    templates = [
        {
            "id": "t1",
            "name": "Workflow",
            "lifecycle_status": "published",
            "phases": [{"name": "P1", "steps": [_strict_step("direct_tool")]}],
        }
    ]
    monkeypatch.setattr(
        readiness,
        "get_service_client",
        lambda: _StubClient(templates, readiness_error='relation "workflow_readiness" does not exist'),
    )
    monkeypatch.setattr(
        readiness,
        "TOOL_REGISTRY",
        {"direct_tool": _fake_tool("direct_tool", "app.agents.tools.content.tools")},
    )

    report = readiness.build_workflow_readiness_report()

    assert report["status"] == "not_ready"
    assert report["checks"]["workflow_readiness_table_accessible"] is False
    assert "workflow_readiness_table_accessible" in report["failing_checks"]


def test_build_workflow_readiness_report_flags_contract_gaps(monkeypatch):
    templates = [
        {
            "id": "t-int",
            "name": "Loose Workflow",
            "lifecycle_status": "published",
            "phases": [{"name": "P1", "steps": [{"name": "S1", "tool": "direct_tool"}]}],
        }
    ]
    readiness_rows = [{"template_id": "t-int", "status": "ready", "required_integrations": []}]

    monkeypatch.setattr(readiness, "get_service_client", lambda: _StubClient(templates, readiness_rows))
    monkeypatch.setattr(
        readiness,
        "TOOL_REGISTRY",
        {"direct_tool": _fake_tool("direct_tool", "app.agents.tools.content.tools")},
    )

    report = readiness.build_workflow_readiness_report()

    assert report["checks"]["user_visible_templates_have_strict_step_contracts"] is True
    assert report["workflow_readiness"]["strict_contract_gaps"] == []


def test_build_workflow_readiness_report_still_flags_missing_tool_schema(monkeypatch):
    templates = [
        {
            "id": "t-int",
            "name": "Loose Workflow",
            "lifecycle_status": "published",
            "phases": [{"name": "P1", "steps": [{"name": "S1", "tool": "direct_tool"}]}],
        }
    ]
    readiness_rows = [{"template_id": "t-int", "status": "ready", "required_integrations": []}]

    monkeypatch.setattr(readiness, "get_service_client", lambda: _StubClient(templates, readiness_rows))
    monkeypatch.setattr(
        readiness,
        "TOOL_REGISTRY",
        {
            "direct_tool": _fake_tool(
                "direct_tool",
                "app.agents.tools.content.tools",
                with_schema=False,
            )
        },
    )

    report = readiness.build_workflow_readiness_report()

    assert report["checks"]["user_visible_templates_have_strict_step_contracts"] is False
    gaps = report["workflow_readiness"]["strict_contract_gaps"]
    assert len(gaps) == 1
    assert "missing typed input schema" in " ".join(gaps[0]["errors"])
