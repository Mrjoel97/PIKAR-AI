# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the Gemini-powered sentiment analysis tool."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(text: str) -> MagicMock:
    """Build a mock Gemini response object."""
    mock = MagicMock()
    mock.text = text
    return mock


def _valid_json_response(
    sentiment: str = "positive",
    confidence: float = 0.85,
) -> str:
    return json.dumps(
        {
            "sentiment": sentiment,
            "confidence": confidence,
            "scores": {
                "positive": 0.85 if sentiment == "positive" else 0.05,
                "negative": 0.05 if sentiment == "positive" else 0.80,
                "neutral": 0.08,
                "mixed": 0.02,
            },
            "summary": f"Text expresses {sentiment} sentiment.",
        }
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_sentiment_positive():
    """Positive text returns sentiment=positive and confidence > 0.5."""
    from app.agents.tools.sentiment_analysis import analyze_sentiment

    mock_response = _make_mock_response(_valid_json_response("positive", 0.9))

    with patch(
        "app.agents.tools.sentiment_analysis._get_genai_client"
    ) as mock_client_fn:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = await analyze_sentiment(query="I love this product, it's amazing!")

    assert result["success"] is True
    assert result["sentiment"] == "positive"
    assert result["confidence"] > 0.5
    assert "scores" in result
    assert "tool" in result
    assert result["tool"] == "analyze_sentiment"


@pytest.mark.asyncio
async def test_analyze_sentiment_negative():
    """Negative text returns sentiment=negative."""
    from app.agents.tools.sentiment_analysis import analyze_sentiment

    mock_response = _make_mock_response(_valid_json_response("negative", 0.8))

    with patch(
        "app.agents.tools.sentiment_analysis._get_genai_client"
    ) as mock_client_fn:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = await analyze_sentiment(query="This is terrible and disappointing!")

    assert result["success"] is True
    assert result["sentiment"] == "negative"
    assert result["confidence"] > 0.5


@pytest.mark.asyncio
async def test_analyze_sentiment_neutral():
    """Neutral text returns sentiment=neutral."""
    from app.agents.tools.sentiment_analysis import analyze_sentiment

    neutral_json = json.dumps(
        {
            "sentiment": "neutral",
            "confidence": 0.7,
            "scores": {"positive": 0.2, "negative": 0.1, "neutral": 0.65, "mixed": 0.05},
            "summary": "Neutral factual statement.",
        }
    )
    mock_response = _make_mock_response(neutral_json)

    with patch(
        "app.agents.tools.sentiment_analysis._get_genai_client"
    ) as mock_client_fn:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = await analyze_sentiment(query="The meeting is at 3pm.")

    assert result["success"] is True
    assert result["sentiment"] == "neutral"


@pytest.mark.asyncio
async def test_analyze_sentiment_empty_query():
    """Empty query returns success=True with a neutral default (no crash)."""
    from app.agents.tools.sentiment_analysis import analyze_sentiment

    neutral_json = json.dumps(
        {
            "sentiment": "neutral",
            "confidence": 0.5,
            "scores": {"positive": 0.25, "negative": 0.25, "neutral": 0.45, "mixed": 0.05},
            "summary": "No text provided.",
        }
    )
    mock_response = _make_mock_response(neutral_json)

    with patch(
        "app.agents.tools.sentiment_analysis._get_genai_client"
    ) as mock_client_fn:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = await analyze_sentiment(query="")

    assert result["success"] is True
    assert result["tool"] == "analyze_sentiment"


@pytest.mark.asyncio
async def test_analyze_sentiment_handles_markdown_fences():
    """Response wrapped in markdown code fences is parsed correctly."""
    from app.agents.tools.sentiment_analysis import analyze_sentiment

    fenced = "```json\n" + _valid_json_response("mixed", 0.6) + "\n```"
    mock_response = _make_mock_response(fenced)

    with patch(
        "app.agents.tools.sentiment_analysis._get_genai_client"
    ) as mock_client_fn:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = await analyze_sentiment(query="It's okay I guess but also kind of great")

    assert result["success"] is True
    assert result["sentiment"] == "mixed"


@pytest.mark.asyncio
async def test_analyze_sentiment_gemini_failure():
    """Gemini exception returns success=False with error message (no crash)."""
    from app.agents.tools.sentiment_analysis import analyze_sentiment

    with patch(
        "app.agents.tools.sentiment_analysis._get_genai_client"
    ) as mock_client_fn:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError(
            "Simulated Gemini failure"
        )
        mock_client_fn.return_value = mock_client

        result = await analyze_sentiment(query="any text")

    assert result["success"] is False
    assert "error" in result
    assert result["tool"] == "analyze_sentiment"


@pytest.mark.asyncio
async def test_analyze_sentiment_scores_structure():
    """Response includes all four score keys."""
    from app.agents.tools.sentiment_analysis import analyze_sentiment

    mock_response = _make_mock_response(_valid_json_response("positive", 0.9))

    with patch(
        "app.agents.tools.sentiment_analysis._get_genai_client"
    ) as mock_client_fn:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = await analyze_sentiment(query="Excellent service!")

    assert result["success"] is True
    scores = result["scores"]
    assert "positive" in scores
    assert "negative" in scores
    assert "neutral" in scores
    assert "mixed" in scores
