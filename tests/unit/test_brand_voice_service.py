# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for BrandVoiceService — brand voice learning from content history."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.brand_voice_service import BrandVoiceService


# ---------------------------------------------------------------------------
# Realistic text samples for testing voice analysis
# ---------------------------------------------------------------------------

# Casual blog posts with contractions, exclamations, questions, short sentences
CASUAL_SAMPLES = [
    (
        "Hey there! So I've been thinking about productivity lately. "
        "Isn't it wild how we're all chasing the same thing? "
        "Here's the deal -- you don't need a fancy app to get stuff done. "
        "Just grab a notebook! Seriously, it works. Trust me on this one."
    ),
    (
        "Okay, let's talk about morning routines. I know, I know -- "
        "everyone's got an opinion. But here's what I've found works: "
        "wake up early, don't check your phone, and move your body. "
        "That's it! Simple, right? You'll thank me later."
    ),
    (
        "I'm SO excited about this new feature we're launching! "
        "It's gonna change everything. Can you believe it? "
        "We've been working on it for months and it's finally here. "
        "Drop a comment if you're as pumped as I am!"
    ),
    (
        "Real talk -- I've made a ton of mistakes in my career. "
        "But here's the thing: that's how you learn. You can't grow "
        "without failing first. So don't beat yourself up! "
        "We're all figuring it out as we go."
    ),
    (
        "Guess what? I just hit 10K followers! Thank you all so much. "
        "It's been an incredible journey. I couldn't have done it without you. "
        "Here's to the next 10K! Let's keep this momentum going!"
    ),
]

# Formal/professional content -- no contractions, longer sentences, no emoji
FORMAL_SAMPLES = [
    (
        "The quarterly financial results demonstrate a sustained improvement "
        "in operational efficiency across all business units. Revenue increased "
        "by 12 percent year-over-year, driven primarily by expansion in the "
        "enterprise segment. Management anticipates continued growth in the "
        "forthcoming fiscal period."
    ),
    (
        "This memorandum outlines the revised procurement policy effective "
        "immediately. All purchase orders exceeding five thousand dollars must "
        "receive approval from the department director prior to submission. "
        "Compliance with these guidelines is mandatory for all personnel."
    ),
    (
        "The research methodology employed in this study utilizes a mixed-methods "
        "approach, combining quantitative survey data with qualitative interview "
        "analysis. The sample population consists of 500 participants selected "
        "through stratified random sampling procedures."
    ),
    (
        "We are pleased to announce the appointment of Dr. Sarah Chen as Chief "
        "Technology Officer. Dr. Chen brings two decades of experience in artificial "
        "intelligence and distributed systems engineering. The board is confident "
        "that her leadership will advance the organization's technological objectives."
    ),
    (
        "The environmental impact assessment indicates that the proposed development "
        "will not significantly affect the surrounding ecosystem. Mitigation measures "
        "have been incorporated into the project design to minimize potential disruptions "
        "to local wildlife habitats and water resources."
    ),
]


class TestAnalyzeContentHistoryMinimum:
    """Test that analysis requires at least 5 content pieces."""

    def test_fewer_than_5_returns_not_ready(self):
        """analyze_content_samples with fewer than 5 items returns not-ready."""
        service = BrandVoiceService()
        result = service.analyze_content_samples(["sample one", "sample two", "sample three"])
        assert result["ready"] is False
        assert "Need at least 5 content pieces" in result["reason"]
        assert "(have 3)" in result["reason"]

    def test_empty_list_returns_not_ready(self):
        """analyze_content_samples with empty list returns not-ready."""
        service = BrandVoiceService()
        result = service.analyze_content_samples([])
        assert result["ready"] is False


class TestAnalyzeContentSamples:
    """Test full analysis with 5+ content pieces."""

    def test_extracts_basic_metrics(self):
        """analyze_content_samples with 5+ items extracts avg_sentence_length, formality_score, common_phrases."""
        service = BrandVoiceService()
        result = service.analyze_content_samples(CASUAL_SAMPLES)
        assert result["ready"] is True
        profile = result["voice_profile"]

        # avg_sentence_length should be a float
        assert isinstance(profile["avg_sentence_length"], float)
        assert profile["avg_sentence_length"] > 0

        # avg_word_count should be a float
        assert isinstance(profile["avg_word_count"], float)
        assert profile["avg_word_count"] > 0

        # formality_score should be between 0 and 1
        assert isinstance(profile["formality_score"], float)
        assert 0.0 <= profile["formality_score"] <= 1.0

        # common_phrases should be a list of strings
        assert isinstance(profile["common_phrases"], list)

    def test_casual_content_low_formality(self):
        """Casual content with contractions and exclamations yields formality_score < 0.4."""
        service = BrandVoiceService()
        result = service.analyze_content_samples(CASUAL_SAMPLES)
        profile = result["voice_profile"]
        assert profile["formality_score"] < 0.4, (
            f"Expected formality < 0.4 for casual content, got {profile['formality_score']}"
        )

    def test_formal_content_high_formality(self):
        """Formal content without contractions yields formality_score > 0.6."""
        service = BrandVoiceService()
        result = service.analyze_content_samples(FORMAL_SAMPLES)
        profile = result["voice_profile"]
        assert profile["formality_score"] > 0.6, (
            f"Expected formality > 0.6 for formal content, got {profile['formality_score']}"
        )


class TestExtractToneMarkers:
    """Test tone marker extraction."""

    def test_extracts_tone_markers(self):
        """extract_tone_markers identifies exclamation_rate, question_rate, emoji_rate."""
        service = BrandVoiceService()
        markers = service.extract_tone_markers(CASUAL_SAMPLES)
        assert "exclamation_rate" in markers
        assert "question_rate" in markers
        assert "emoji_rate" in markers
        assert "formality_score" in markers

        # Casual content has exclamations and questions
        assert markers["exclamation_rate"] > 0
        assert markers["question_rate"] > 0
        assert isinstance(markers["formality_score"], float)

    def test_formal_low_exclamation_rate(self):
        """Formal content has low exclamation rate."""
        service = BrandVoiceService()
        markers = service.extract_tone_markers(FORMAL_SAMPLES)
        assert markers["exclamation_rate"] == 0.0


class TestExtractVocabularyPatterns:
    """Test vocabulary pattern extraction."""

    def test_returns_distinctive_words(self):
        """extract_vocabulary_patterns returns top distinctive words."""
        service = BrandVoiceService()
        vocab = service.extract_vocabulary_patterns(CASUAL_SAMPLES)
        assert "distinctive_words" in vocab
        assert isinstance(vocab["distinctive_words"], list)
        # Should return up to 20 words
        assert len(vocab["distinctive_words"]) <= 20

    def test_excludes_stopwords(self):
        """Distinctive words exclude common stopwords."""
        service = BrandVoiceService()
        vocab = service.extract_vocabulary_patterns(CASUAL_SAMPLES)
        stopwords = {"the", "a", "an", "is", "it", "and", "or", "but", "in", "on", "to", "of"}
        for word in vocab["distinctive_words"]:
            assert word.lower() not in stopwords, f"Stopword '{word}' should be excluded"

    def test_avg_word_length(self):
        """extract_vocabulary_patterns returns avg_word_length."""
        service = BrandVoiceService()
        vocab = service.extract_vocabulary_patterns(FORMAL_SAMPLES)
        assert "avg_word_length" in vocab
        assert isinstance(vocab["avg_word_length"], float)
        assert vocab["avg_word_length"] > 0


class TestBuildVoiceProfile:
    """Test voice profile compilation."""

    def test_build_voice_profile(self):
        """build_voice_profile compiles features into structured profile dict."""
        service = BrandVoiceService()
        tone = {"exclamation_rate": 0.3, "question_rate": 0.2, "emoji_rate": 0.0, "formality_score": 0.25}
        vocab = {"distinctive_words": ["productivity", "morning", "routine"], "avg_word_length": 5.2}
        sentences = {"avg_sentence_length": 8.5, "sentence_length_variance": 3.2, "short_sentence_ratio": 0.4}

        profile = service.build_voice_profile(tone, vocab, sentences)

        assert "tone_summary" in profile
        assert "personality_traits" in profile
        assert isinstance(profile["personality_traits"], list)
        assert len(profile["personality_traits"]) > 0
        assert "example_sentences" in profile
        assert "formality_score" in profile


class TestPersistVoiceToBrandProfile:
    """Test persisting learned voice to brand profile."""

    @pytest.mark.asyncio
    async def test_persist_calls_update_brand_profile(self):
        """persist_voice_to_brand_profile calls update_brand_profile with learned voice fields."""
        service = BrandVoiceService()
        voice_profile = {
            "tone_summary": "conversational and enthusiastic",
            "personality_traits": ["witty", "energetic", "approachable"],
            "example_sentences": [
                "Hey there! So I've been thinking about productivity lately.",
                "Real talk -- I've made a ton of mistakes in my career.",
                "Guess what? I just hit 10K followers!",
            ],
            "formality_score": 0.25,
        }

        with patch(
            "app.services.brand_voice_service.update_brand_profile",
            new_callable=AsyncMock,
            return_value={"success": True, "action": "updated"},
        ) as mock_update:
            result = await service.persist_voice_to_brand_profile("user-123", voice_profile)

            mock_update.assert_called_once_with(
                voice_tone="conversational and enthusiastic",
                voice_personality=["witty", "energetic", "approachable"],
                voice_examples=(
                    "Hey there! So I've been thinking about productivity lately. | "
                    "Real talk -- I've made a ton of mistakes in my career. | "
                    "Guess what? I just hit 10K followers!"
                ),
                user_id="user-123",
            )
            assert result["success"] is True


class TestAnalyzeAndLearn:
    """Test the full pipeline: fetch -> analyze -> persist."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_enough_content(self):
        """analyze_and_learn fetches content, analyzes, and persists when 5+ pieces exist."""
        service = BrandVoiceService()

        # Mock ContentService.list_content
        mock_content = [{"content": text, "title": f"Post {i}"} for i, text in enumerate(CASUAL_SAMPLES)]

        with (
            patch.object(
                service,
                "get_content_history",
                new_callable=AsyncMock,
                return_value=[item["content"] for item in mock_content],
            ),
            patch.object(
                service,
                "persist_voice_to_brand_profile",
                new_callable=AsyncMock,
                return_value={"success": True, "action": "updated"},
            ) as mock_persist,
        ):
            result = await service.analyze_and_learn("user-123")

            assert result["success"] is True
            assert "voice_profile" in result
            mock_persist.assert_called_once()
            # Check that user_id was passed
            call_args = mock_persist.call_args
            assert call_args[0][0] == "user-123"

    @pytest.mark.asyncio
    async def test_full_pipeline_insufficient_content(self):
        """analyze_and_learn returns not-ready when fewer than 5 pieces."""
        service = BrandVoiceService()

        with patch.object(
            service,
            "get_content_history",
            new_callable=AsyncMock,
            return_value=["text one", "text two"],
        ):
            result = await service.analyze_and_learn("user-123")

            assert result["success"] is False
            assert "Need at least 5" in result["reason"]
