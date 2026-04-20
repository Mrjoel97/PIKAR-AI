from app.workflows.contract_defaults import (
    INTEGRATION_SETUP_GUIDE,
    TOOL_REQUIRED_INTEGRATIONS,
    enrich_template_phases_for_execution,
    list_contract_safe_tool_names,
    normalize_template_for_execution,
)


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
    assert "mcp_web_scrape" in tools  # now included in SAFE_WORKFLOW_TOOL_ORDER
    assert "generate_invoice" not in tools


def test_tool_required_integrations_cover_remaining_readiness_workflows():
    assert TOOL_REQUIRED_INTEGRATIONS["start_call"] == ["email"]
    assert TOOL_REQUIRED_INTEGRATIONS["ocr_document"] == ["google_ai"]
    assert TOOL_REQUIRED_INTEGRATIONS["upload_file"] == ["supabase"]
    assert TOOL_REQUIRED_INTEGRATIONS["process_payment"] == ["supabase"]
    assert TOOL_REQUIRED_INTEGRATIONS["book_travel"] == ["supabase"]


def test_integration_setup_guide_includes_runtime_aliases():
    assert INTEGRATION_SETUP_GUIDE["email"]["env_var"] == "RESEND_API_KEY"
    assert INTEGRATION_SETUP_GUIDE["crm"]["env_var"] == "HUBSPOT_API_KEY"
    assert "SUPABASE_URL" in INTEGRATION_SETUP_GUIDE["supabase"]["env_var"]


def test_normalize_template_for_execution_enriches_legacy_template_payload():
    normalized = normalize_template_for_execution(
        {
            "name": "Legacy Workflow",
            "description": "Backfill missing step contract fields",
            "category": "operations",
            "phases": [
                {
                    "name": "Phase 1",
                    "steps": [{"name": "Draft Email", "tool": "send_email"}],
                }
            ],
        }
    )

    step = normalized["phases"][0]["steps"][0]
    assert step["tool"] == "send_email"
    assert step["input_bindings"]
    assert step["expected_outputs"]
    assert isinstance(step["allow_parallel"], bool)
