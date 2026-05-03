from pathlib import Path

from app.agents.tools import integration_setup


class _Config:
    def is_tavily_configured(self):
        return False

    def is_firecrawl_configured(self):
        return False

    def is_stitch_configured(self):
        return False

    def is_email_configured(self):
        return True

    def is_crm_configured(self):
        return False

    def is_supabase_configured(self):
        return True

    def is_google_seo_configured(self):
        return False

    def is_google_analytics_configured(self):
        return False


def test_check_integration_status_exposes_runtime_aliases(monkeypatch):
    monkeypatch.setattr(
        "app.mcp.config.get_mcp_config",
        lambda: _Config(),
    )

    result = integration_setup.check_integration_status()

    assert result["integrations"]["tavily"]["configured"] is True
    assert result["integrations"]["tavily"]["platform_managed"] is True
    assert result["integrations"]["email"]["configured"] is True
    assert result["integrations"]["crm"]["configured"] is False
    assert result["integrations"]["supabase"]["configured"] is True


def test_get_workflow_requirements_uses_runtime_alias_checks(monkeypatch):
    monkeypatch.setattr(
        "app.mcp.config.get_mcp_config",
        lambda: _Config(),
    )
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "alias_workflow.yaml"
    monkeypatch.setattr(
        Path,
        "glob",
        lambda self, pattern: [fixture],
    )

    result = integration_setup.get_workflow_requirements("Alias Workflow")

    assert result["success"] is True
    details_by_id = {item["id"]: item for item in result["required_integrations"]}
    assert details_by_id["supabase"]["configured"] is True
    assert details_by_id["email"]["configured"] is True


def test_get_setup_guide_marks_built_in_research_as_platform_managed():
    result = integration_setup.get_setup_guide("tavily")

    assert result["success"] is True
    assert result["configured"] is True
    assert result["platform_managed"] is True
    assert result["setup_required"] is False
    assert "No user setup required" in result["setup_steps"]
