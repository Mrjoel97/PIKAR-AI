from pathlib import Path

from app.agents.tools import integration_setup


class _Config:
    def is_tavily_configured(self):
        return True

    def is_firecrawl_configured(self):
        return True

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
