from app.workflows.contract_defaults import enrich_template_phases_for_execution, list_contract_safe_tool_names


def test_enrich_template_phases_adds_strict_metadata_for_create_task():
    phases = [
        {
            "name": "Capture",
            "steps": [
                {
                    "name": "Create Follow-Up Task",
                    "tool": "create_task",
                    "description": "Capture founder assumptions and next actions",
                }
            ],
        }
    ]

    enriched = enrich_template_phases_for_execution(
        phases,
        template_name="Idea Sprint",
        category="strategy",
        persona="startup",
        goal="Validate a new SaaS offer",
    )

    step = enriched[0]["steps"][0]
    assert step["input_bindings"]["description"]["value"] == "Capture founder assumptions and next actions"
    assert step["risk_level"] == "medium"
    assert step["expected_outputs"] == ["task.id"]
    assert step["verification_checks"][0] == "success"
    assert step["allow_parallel"] is False


def test_list_contract_safe_tool_names_only_returns_publishable_generation_tools():
    tools = list_contract_safe_tool_names()

    assert "create_task" in tools
    assert "mcp_web_search" in tools
    assert "create_report" in tools
    assert "mcp_web_scrape" not in tools
    assert "generate_invoice" not in tools
