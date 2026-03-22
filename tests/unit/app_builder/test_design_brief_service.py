"""Unit tests for design_brief_service — mocked Tavily, Gemini, and Supabase."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Test 1: run_design_research calls TavilySearchTool and yields step events
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_calls_tavily():
    """run_design_research calls TavilySearchTool.search at least twice and yields step events."""
    fake_results = {
        "success": True,
        "results": [{"title": "Bakery Design Trends", "content": "Warm tones, organic shapes"}],
        "answer": "Warm bakery aesthetics",
    }

    mock_tavily_instance = MagicMock()
    mock_tavily_instance.search = AsyncMock(return_value=fake_results)

    mock_genai_response = MagicMock()
    mock_genai_response.text = (
        "DESIGN_SYSTEM_MARKDOWN:\n# Design\nWarm and earthy.\n"
        "PALETTE:\n[{\"hex\": \"#F5E6D3\", \"name\": \"Warm Cream\"}]\n"
        "TYPOGRAPHY:\n{\"heading\": \"Playfair Display\", \"body\": \"Lato\", \"scale\": \"1.25\"}\n"
        "SPACING:\n{\"base_unit\": 8, \"section_padding\": 64, \"card_padding\": 24}\n"
        "SITEMAP_JSON:\n[{\"page\": \"home\", \"title\": \"Home\", \"sections\": [\"hero\"], \"device_targets\": [\"DESKTOP\"]}]\n"
    )

    mock_genai_client = MagicMock()
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_genai_response)

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{}])
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    with (
        patch("app.services.design_brief_service.TavilySearchTool", return_value=mock_tavily_instance),
        patch("app.services.design_brief_service.genai") as mock_genai_mod,
        patch("app.services.design_brief_service.get_service_client", return_value=mock_supabase),
    ):
        mock_genai_mod.Client.return_value = mock_genai_client

        from app.services.design_brief_service import run_design_research  # noqa: PLC0415

        events = []
        async for event in run_design_research(
            creative_brief={"what": "bakery website", "vibe": "warm"},
            project_id="test-id",
            user_id="user-id",
        ):
            events.append(event)

    assert mock_tavily_instance.search.call_count >= 2, (
        f"Expected at least 2 Tavily calls, got {mock_tavily_instance.search.call_count}"
    )

    steps = [e["step"] for e in events]
    assert "searching" in steps
    assert "synthesizing" in steps
    assert "saving" in steps
    assert "ready" in steps


# ---------------------------------------------------------------------------
# Test 2: Gemini prompt contains flattened research text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesis_uses_research():
    """Gemini generate_content receives flattened research results in its prompt."""
    fake_results = {
        "success": True,
        "results": [{"title": "Artisan Bakery", "content": "Sourdough and pastries thrive with warm palettes"}],
        "answer": "Warm aesthetics",
    }

    mock_tavily_instance = MagicMock()
    mock_tavily_instance.search = AsyncMock(return_value=fake_results)

    mock_genai_response = MagicMock()
    mock_genai_response.text = (
        "DESIGN_SYSTEM_MARKDOWN:\n# Design\n"
        "PALETTE:\n[{\"hex\": \"#F5E6D3\", \"name\": \"Warm Cream\"}]\n"
        "TYPOGRAPHY:\n{\"heading\": \"Playfair Display\", \"body\": \"Lato\", \"scale\": \"1.25\"}\n"
        "SPACING:\n{\"base_unit\": 8, \"section_padding\": 64, \"card_padding\": 24}\n"
        "SITEMAP_JSON:\n[{\"page\": \"home\", \"title\": \"Home\", \"sections\": [\"hero\"], \"device_targets\": [\"DESKTOP\"]}]\n"
    )

    mock_generate = AsyncMock(return_value=mock_genai_response)
    mock_genai_client = MagicMock()
    mock_genai_client.aio.models.generate_content = mock_generate

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{}])
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    with (
        patch("app.services.design_brief_service.TavilySearchTool", return_value=mock_tavily_instance),
        patch("app.services.design_brief_service.genai") as mock_genai_mod,
        patch("app.services.design_brief_service.get_service_client", return_value=mock_supabase),
    ):
        mock_genai_mod.Client.return_value = mock_genai_client

        from app.services.design_brief_service import run_design_research  # noqa: PLC0415

        async for _ in run_design_research(
            creative_brief={"what": "artisan bakery", "vibe": "rustic"},
            project_id="proj-123",
            user_id="user-123",
        ):
            pass

    assert mock_generate.called, "Gemini generate_content was not called"
    call_kwargs = mock_generate.call_args
    # contents arg is either positional or keyword
    contents_arg = (
        call_kwargs.kwargs.get("contents")
        or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else "")
    )
    assert "Sourdough and pastries" in contents_arg or "Artisan Bakery" in contents_arg, (
        f"Research text not found in Gemini prompt. Got: {contents_arg[:200]}"
    )


# ---------------------------------------------------------------------------
# Test 3: _parse_design_response extracts structured fields
# ---------------------------------------------------------------------------


def test_parse_design_response():
    """_parse_design_response extracts colors, typography, spacing, sitemap, raw_markdown."""
    from app.services.design_brief_service import _parse_design_response  # noqa: PLC0415

    sample_response = (
        "DESIGN_SYSTEM_MARKDOWN:\n"
        "# Bakery Design System\n"
        "Warm earthy tones with artisan feel.\n"
        "PALETTE:\n"
        '[{"hex": "#F5E6D3", "name": "Warm Cream"}, {"hex": "#8B4513", "name": "Saddle Brown"}]\n'
        "TYPOGRAPHY:\n"
        '{"heading": "Playfair Display", "body": "Lato", "scale": "1.25"}\n'
        "SPACING:\n"
        '{"base_unit": 8, "section_padding": 64, "card_padding": 24}\n'
        "SITEMAP_JSON:\n"
        '[{"page": "home", "title": "Homepage", "sections": ["hero", "features"], "device_targets": ["DESKTOP", "MOBILE"]},'
        ' {"page": "about", "title": "About", "sections": ["story"], "device_targets": ["DESKTOP"]}]\n'
    )

    result = _parse_design_response(sample_response)

    assert "colors" in result
    assert isinstance(result["colors"], list)
    assert len(result["colors"]) == 2
    assert result["colors"][0]["hex"] == "#F5E6D3"

    assert "typography" in result
    assert isinstance(result["typography"], dict)
    assert "heading" in result["typography"]
    assert "body" in result["typography"]
    assert result["typography"]["heading"] == "Playfair Display"

    assert "spacing" in result
    assert isinstance(result["spacing"], dict)
    assert "base_unit" in result["spacing"]
    assert result["spacing"]["base_unit"] == 8

    assert "raw_markdown" in result
    assert isinstance(result["raw_markdown"], str)
    assert "Bakery Design System" in result["raw_markdown"]

    assert "sitemap" in result
    assert isinstance(result["sitemap"], list)
    assert len(result["sitemap"]) == 2
    assert result["sitemap"][0]["page"] == "home"


# ---------------------------------------------------------------------------
# Test 4: _generate_build_plan returns structured phase list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_plan_structure():
    """_generate_build_plan returns list of phases with required keys."""
    build_plan_response = json.dumps([
        {
            "phase": 1,
            "label": "Home Screen",
            "screens": [
                {"name": "Homepage Desktop", "page": "home", "device": "DESKTOP"},
                {"name": "Homepage Mobile", "page": "home", "device": "MOBILE"},
            ],
            "dependencies": [],
        },
        {
            "phase": 2,
            "label": "About Screen",
            "screens": [
                {"name": "About Desktop", "page": "about", "device": "DESKTOP"},
            ],
            "dependencies": [1],
        },
    ])

    mock_genai_response = MagicMock()
    mock_genai_response.text = build_plan_response

    mock_genai_client = MagicMock()
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_genai_response)

    with patch("app.services.design_brief_service.genai") as mock_genai_mod:
        mock_genai_mod.Client.return_value = mock_genai_client

        from app.services.design_brief_service import _generate_build_plan  # noqa: PLC0415

        result = await _generate_build_plan(
            sitemap=[
                {
                    "page": "home",
                    "title": "Homepage",
                    "sections": ["hero", "features"],
                    "device_targets": ["DESKTOP", "MOBILE"],
                },
                {
                    "page": "about",
                    "title": "About",
                    "sections": ["story"],
                    "device_targets": ["DESKTOP"],
                },
            ],
            design_system={"colors": []},
        )

    assert isinstance(result, list)
    assert len(result) == 2

    for phase in result:
        assert "phase" in phase, f"Missing 'phase' key in: {phase}"
        assert "label" in phase, f"Missing 'label' key in: {phase}"
        assert "screens" in phase, f"Missing 'screens' key in: {phase}"
        assert "dependencies" in phase, f"Missing 'dependencies' key in: {phase}"
        assert isinstance(phase["screens"], list)
        assert isinstance(phase["dependencies"], list)
        for screen in phase["screens"]:
            assert "name" in screen
            assert "page" in screen
            assert "device" in screen
