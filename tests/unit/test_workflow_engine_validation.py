from app.workflows.engine import validate_template_phases


def test_validate_template_phases_accepts_valid_schema():
    phases = [
        {
            "name": "Plan",
            "steps": [
                {"name": "Collect Input", "tool": "create_task"},
                {"name": "Research", "tool": "mcp_web_search"},
            ],
        }
    ]
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

