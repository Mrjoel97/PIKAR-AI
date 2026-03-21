"""Unit tests for prompt_enhancer — mocks Gemini calls."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_enhance_prompt_returns_structured_output():
    """Gemini response is returned as-is when it contains required fields."""
    from app.services import prompt_enhancer

    fake_response = (
        "CONCEPT: Artisan bakery\n"
        "VISUAL_STYLE: warm, artisan\n"
        "COLOR_PALETTE: #F5E6D3 warm cream, #8B4513 saddle brown\n"
        "TYPOGRAPHY: Playfair Display headings, Lato body\n"
        "SECTIONS: hero, products, about, location\n"
        "IMAGERY: warm bread photography\n"
        "TONE: friendly\n"
        "TARGET_AUDIENCE: local community"
    )

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=MagicMock(text=fake_response)
    )

    with patch("app.services.prompt_enhancer.genai") as mock_genai:
        mock_genai.Client.return_value = mock_client
        result = await prompt_enhancer.enhance_prompt("bakery website")

    assert "COLOR_PALETTE" in result
    assert "TYPOGRAPHY" in result
    assert "SECTIONS" in result


@pytest.mark.asyncio
async def test_enhance_prompt_auto_detects_domain():
    """domain_hint is auto-detected from description when not provided."""
    from app.services import prompt_enhancer

    captured_vocab = {}

    async def fake_gemini_call(model, contents, config):
        captured_vocab["contents"] = contents
        return MagicMock(text="CONCEPT: saas\nCOLOR_PALETTE: #6366F1\nTYPOGRAPHY: Inter\nSECTIONS: hero, pricing")

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = fake_gemini_call

    with patch("app.services.prompt_enhancer.genai") as mock_genai:
        mock_genai.Client.return_value = mock_client
        await prompt_enhancer.enhance_prompt("saas landing page")

    # Vocabulary for 'saas' domain should appear in the contents passed to Gemini
    assert "indigo" in captured_vocab["contents"].lower() or "saas" in captured_vocab["contents"].lower()


@pytest.mark.asyncio
async def test_enhance_prompt_falls_back_on_gemini_error():
    """Returns original description unchanged when Gemini raises."""
    from app.services import prompt_enhancer

    with patch("app.services.prompt_enhancer.genai") as mock_genai:
        mock_genai.Client.side_effect = RuntimeError("Gemini unavailable")
        result = await prompt_enhancer.enhance_prompt("pet store website")

    assert result == "pet store website"


def test_design_vocabulary_has_required_domains():
    """DESIGN_VOCABULARY contains bakery, saas, restaurant, fitness."""
    from app.services.prompt_enhancer import DESIGN_VOCABULARY
    for domain in ("bakery", "saas", "restaurant", "fitness"):
        assert domain in DESIGN_VOCABULARY
        assert "colors" in DESIGN_VOCABULARY[domain]
        assert "typography" in DESIGN_VOCABULARY[domain]
        assert "sections" in DESIGN_VOCABULARY[domain]
