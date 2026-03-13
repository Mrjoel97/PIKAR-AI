from app.workflows.engine import validate_template_phases


def _strict_step(tool: str, *, risk_level: str = "medium", required_approval: bool = False):
    return {
        "name": "Step",
        "tool": tool,
        "required_approval": required_approval,
        "input_bindings": {"description": {"value": "do work"}} if tool == "create_task" else {"query": {"value": "market"}},
        "risk_level": risk_level,
        "required_integrations": [],
        "verification_checks": ["success"],
        "expected_outputs": ["task.id"] if tool == "create_task" else ["results"],
        "allow_parallel": False,
    }


def test_validate_template_phases_accepts_valid_schema():
    phases = [{"name": "Plan", "steps": [_strict_step("create_task")]}]
    errors = validate_template_phases(phases, {"create_task", "mcp_web_search"})
    assert errors == []


def test_validate_template_phases_rejects_missing_fields_and_unknown_tool():
    phases = [{"name": "", "steps": [{"name": "", "tool": "unknown_tool"}]}]
    errors = validate_template_phases(phases, {"create_task"})
    assert any("missing non-empty name" in e for e in errors)
    assert any("unresolved tool 'unknown_tool'" in e for e in errors)


def test_validate_template_phases_rejects_deprecated_tool():
    phases = [{"name": "Legal", "steps": [{"name": "Offer", "tool": "sent_contract"}]}]
    errors = validate_template_phases(phases, {"sent_contract"})
    assert any("deprecated tool 'sent_contract'" in e for e in errors)


def test_validate_template_phases_rejects_missing_strict_contract_metadata():
    phases = [{"name": "Plan", "steps": [{"name": "Collect Input", "tool": "create_task"}]}]
    errors = validate_template_phases(
        phases,
        {"create_task"},
        strict_user_visible=True,
        tool_registry={},
    )
    assert any("missing non-empty input_bindings" in e for e in errors)
    assert any("missing valid risk_level" in e for e in errors)
    assert any("missing non-empty expected_outputs list" in e for e in errors)
