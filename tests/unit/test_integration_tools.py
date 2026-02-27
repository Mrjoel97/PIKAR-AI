import pytest

from app.agents.tools import integration_tools


def _set_integration_mode(
    monkeypatch,
    *,
    allow_fallback_simulation: bool = True,
    strict_critical_tool_guard: bool = False,
):
    monkeypatch.setenv(
        "WORKFLOW_ALLOW_FALLBACK_SIMULATION",
        "true" if allow_fallback_simulation else "false",
    )
    monkeypatch.setenv(
        "WORKFLOW_STRICT_CRITICAL_TOOL_GUARD",
        "true" if strict_critical_tool_guard else "false",
    )


class _Cfg:
    def __init__(self, email=False, crm=False):
        self._email = email
        self._crm = crm

    def is_email_configured(self):
        return self._email

    def is_crm_configured(self):
        return self._crm


@pytest.mark.asyncio
async def test_send_message_uses_email_integration(monkeypatch):
    _set_integration_mode(monkeypatch, allow_fallback_simulation=True, strict_critical_tool_guard=False)
    monkeypatch.setattr(integration_tools, "get_mcp_config", lambda: _Cfg(email=True))

    called = {"email": False}

    async def _send_notification_email(**kwargs):
        called["email"] = True
        return {"success": True, "message": "sent"}

    async def _track_event(*_args, **_kwargs):
        return {"success": True}

    monkeypatch.setattr(integration_tools, "send_notification_email", _send_notification_email)
    monkeypatch.setattr(integration_tools, "track_event", _track_event)

    result = await integration_tools.send_message(
        to=["a@example.com"],
        subject="Hello",
        body="World",
    )
    assert result["success"] is True
    assert result["status"] == "integrated"
    assert called["email"] is True


@pytest.mark.asyncio
async def test_send_message_fallback_creates_task(monkeypatch):
    _set_integration_mode(monkeypatch, allow_fallback_simulation=True, strict_critical_tool_guard=False)
    monkeypatch.setattr(integration_tools, "get_mcp_config", lambda: _Cfg(email=False, crm=False))

    async def _create_task(description: str):
        return {"success": True, "task": {"id": "task-1", "description": description}}

    async def _track_event(*_args, **_kwargs):
        return {"success": True}

    monkeypatch.setattr(integration_tools, "create_task", _create_task)
    monkeypatch.setattr(integration_tools, "track_event", _track_event)

    result = await integration_tools.send_message(to=["a@example.com"], subject="Fallback")
    assert result["success"] is True
    assert result["status"] == "fallback"
    assert "task" in result


@pytest.mark.asyncio
async def test_send_message_strict_missing_email_integration_fails(monkeypatch):
    _set_integration_mode(monkeypatch, allow_fallback_simulation=False, strict_critical_tool_guard=True)
    monkeypatch.setattr(integration_tools, "get_mcp_config", lambda: _Cfg(email=False, crm=False))

    created_task = {"called": False}

    async def _create_task(description: str):
        created_task["called"] = True
        return {"success": True, "task": {"id": "task-1", "description": description}}

    async def _track_event(*_args, **_kwargs):
        return {"success": True}

    monkeypatch.setattr(integration_tools, "create_task", _create_task)
    monkeypatch.setattr(integration_tools, "track_event", _track_event)

    result = await integration_tools.send_message(to=["a@example.com"], subject="Strict")
    assert result["success"] is False
    assert result["status"] == "failed"
    assert result["error_code"] == "integration_not_configured"
    assert result["required_integrations"] == ["email"]
    assert result["strict_integration_mode"] is True
    assert created_task["called"] is False


@pytest.mark.asyncio
async def test_send_message_strict_missing_crm_integration_fails(monkeypatch):
    _set_integration_mode(monkeypatch, allow_fallback_simulation=False, strict_critical_tool_guard=True)
    monkeypatch.setattr(integration_tools, "get_mcp_config", lambda: _Cfg(email=False, crm=False))

    created_task = {"called": False}

    async def _create_task(description: str):
        created_task["called"] = True
        return {"success": True, "task": {"id": "task-1", "description": description}}

    async def _track_event(*_args, **_kwargs):
        return {"success": True}

    monkeypatch.setattr(integration_tools, "create_task", _create_task)
    monkeypatch.setattr(integration_tools, "track_event", _track_event)

    result = await integration_tools.send_message(
        channel="crm",
        email="crm@example.com",
        subject="Strict CRM",
    )
    assert result["success"] is False
    assert result["status"] == "failed"
    assert result["error_code"] == "integration_not_configured"
    assert result["required_integrations"] == ["crm"]
    assert result["channel"] == "crm"
    assert created_task["called"] is False


@pytest.mark.asyncio
async def test_create_connection_supabase_probe(monkeypatch):
    _set_integration_mode(monkeypatch, allow_fallback_simulation=True, strict_critical_tool_guard=False)
    class _Query:
        def select(self, *_a, **_k):
            return self

        def limit(self, *_a, **_k):
            return self

        def execute(self):
            class _Resp:
                data = [{"id": "t1"}]

            return _Resp()

    class _Client:
        def table(self, _name):
            return _Query()

    async def _save_content(title: str, content: str):
        return {"success": True, "content": {"title": title, "content": content}}

    async def _track_event(*_args, **_kwargs):
        return {"success": True}

    monkeypatch.setattr(integration_tools, "get_service_client", lambda: _Client())
    monkeypatch.setattr(integration_tools, "save_content", _save_content)
    monkeypatch.setattr(integration_tools, "track_event", _track_event)

    result = await integration_tools.create_connection(connection_name="primary", connection_type="supabase")
    assert result["success"] is True
    assert result["probe"]["tested"] is True
    assert result["probe"]["ok"] is True


@pytest.mark.asyncio
async def test_create_connection_strict_supabase_probe_failure_returns_failed(monkeypatch):
    _set_integration_mode(monkeypatch, allow_fallback_simulation=False, strict_critical_tool_guard=True)

    class _Client:
        def table(self, _name):
            raise RuntimeError("supabase not configured")

    async def _save_content(title: str, content: str):
        return {"success": True, "content": {"title": title, "content": content}}

    async def _track_event(*_args, **_kwargs):
        return {"success": True}

    monkeypatch.setattr(integration_tools, "get_service_client", lambda: _Client())
    monkeypatch.setattr(integration_tools, "save_content", _save_content)
    monkeypatch.setattr(integration_tools, "track_event", _track_event)

    result = await integration_tools.create_connection(connection_name="primary", connection_type="supabase")
    assert result["success"] is False
    assert result["status"] == "failed"
    assert result["error_code"] == "integration_not_configured"
    assert result["required_integrations"] == ["supabase"]
    assert result["probe"]["tested"] is True
    assert result["probe"]["ok"] is False


@pytest.mark.asyncio
async def test_audit_logs_reads_supabase_table(monkeypatch):
    _set_integration_mode(monkeypatch, allow_fallback_simulation=True, strict_critical_tool_guard=False)
    rows = [{"tool_name": "send_message", "success": True}]

    class _Query:
        def __init__(self):
            self._rows = rows

        def select(self, *_a, **_k):
            return self

        def order(self, *_a, **_k):
            return self

        def limit(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def execute(self):
            class _Resp:
                data = rows

            return _Resp()

    class _Client:
        def table(self, _name):
            return _Query()

    async def _track_event(*_args, **_kwargs):
        return {"success": True}

    monkeypatch.setattr(integration_tools, "get_service_client", lambda: _Client())
    monkeypatch.setattr(integration_tools, "track_event", _track_event)

    result = await integration_tools.audit_logs(limit=5)
    assert result["success"] is True
    assert result["status"] == "integrated"
    assert result["count"] == 1


@pytest.mark.asyncio
async def test_start_call_strict_missing_email_integration_fails(monkeypatch):
    _set_integration_mode(monkeypatch, allow_fallback_simulation=False, strict_critical_tool_guard=True)
    monkeypatch.setattr(integration_tools, "get_mcp_config", lambda: _Cfg(email=False))

    async def _save_content(title: str, content: str):
        return {"success": True, "content": {"title": title, "content": content}}

    async def _track_event(*_args, **_kwargs):
        return {"success": True}

    sent = {"called": False}

    async def _send_notification_email(**kwargs):
        sent["called"] = True
        return {"success": True}

    monkeypatch.setattr(integration_tools, "save_content", _save_content)
    monkeypatch.setattr(integration_tools, "track_event", _track_event)
    monkeypatch.setattr(integration_tools, "send_notification_email", _send_notification_email)

    result = await integration_tools.start_call(
        participant="Client",
        purpose="Renewal",
        to=["client@example.com"],
    )
    assert result["success"] is False
    assert result["status"] == "failed"
    assert result["error_code"] == "integration_not_configured"
    assert result["required_integrations"] == ["email"]
    assert result["tool"] == "start_call"
    assert "note" in result
    assert sent["called"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "kwargs"),
    [
        ("run_script", {"script_name": "nightly"}),
        ("run_deployment", {"service": "api", "environment": "staging"}),
        ("process_forms", {"form_name": "lead_capture", "submission_id": "sub-1"}),
        ("update_code", {"repo": "pikar-ai", "branch": "main", "summary": "refresh docs"}),
        ("train_model", {"model_name": "classifier", "dataset": "events"}),
        ("deploy_service", {"service_name": "worker", "environment": "prod"}),
        ("create_chart", {"name": "Revenue", "chart_type": "line", "data_query": "select * from revenue"}),
        ("process_data", {"pipeline_name": "daily", "input_source": "events", "operation": "aggregate"}),
    ],
)
async def test_new_tier_b_tools_return_integrated(monkeypatch, tool_name, kwargs):
    _set_integration_mode(monkeypatch, allow_fallback_simulation=True, strict_critical_tool_guard=False)
    async def _save_content(title: str, content: str):
        return {"success": True, "content": {"title": title, "content": content}}

    async def _create_task(description: str):
        return {"success": True, "task": {"description": description}}

    async def _create_report(title: str, report_type: str, data: str, description: str = None):
        return {"success": True, "report": {"title": title, "report_type": report_type, "data": data, "description": description}}

    async def _track_event(*_args, **_kwargs):
        return {"success": True}

    monkeypatch.setattr(integration_tools, "save_content", _save_content)
    monkeypatch.setattr(integration_tools, "create_task", _create_task)
    monkeypatch.setattr(integration_tools, "create_report", _create_report)
    monkeypatch.setattr(integration_tools, "track_event", _track_event)

    fn = getattr(integration_tools, tool_name)
    result = await fn(**kwargs)
    assert result["success"] is True
    assert result["status"] == "integrated"
    assert result["tool"] == tool_name
