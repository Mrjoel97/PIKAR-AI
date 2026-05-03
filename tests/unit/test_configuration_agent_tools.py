from app.agents.tools import configuration as configuration_tools


def test_get_available_tools_marks_built_in_research_platform_managed(monkeypatch):
    monkeypatch.delenv("STITCH_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    result = configuration_tools.get_available_tools()

    built_in_by_id = {tool["id"]: tool for tool in result["built_in_tools"]}
    assert built_in_by_id["tavily"]["configured"] is True
    assert built_in_by_id["tavily"]["platform_managed"] is True
    assert built_in_by_id["tavily"]["status"] == "Active for all users"
    assert built_in_by_id["firecrawl"]["configured"] is True
    assert "active for all users" in result["summary"].lower()
    assert "platform-managed" in result["message"].lower()
