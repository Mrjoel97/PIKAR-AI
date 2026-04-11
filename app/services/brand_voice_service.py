# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""BrandVoiceService — Automatic brand voice learning from content history.

Analyzes a user's content history (5+ pieces) to extract tone, vocabulary,
and style patterns. Learned patterns are persisted to the brand profile so
all future content generation reflects the user's natural writing voice.

Uses only stdlib (re, collections) — no external NLP dependencies.
"""

import logging
import re
from collections import Counter

from app.agents.tools.brand_profile import update_brand_profile

logger = logging.getLogger(__name__)

# Common English stopwords to exclude from distinctive word analysis
_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "its", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "this", "that", "these", "those", "i", "me", "my", "we", "our",
    "you", "your", "he", "she", "his", "her", "they", "them", "their",
    "not", "no", "so", "if", "as", "up", "out", "about", "than", "then",
    "just", "also", "very", "all", "any", "each", "more", "most", "some",
    "such", "only", "own", "same", "too", "into", "over", "after", "what",
    "which", "who", "how", "when", "where", "why", "here", "there",
    "am", "get", "got", "don", "t", "s", "re", "ve", "ll", "d", "m",
})

# Common English contractions for formality detection
_CONTRACTIONS_PATTERN = re.compile(
    r"\b(?:i'm|i've|i'll|i'd|you're|you've|you'll|you'd|he's|she's|it's|"
    r"we're|we've|we'll|we'd|they're|they've|they'll|they'd|"
    r"isn't|aren't|wasn't|weren't|hasn't|haven't|hadn't|"
    r"doesn't|don't|didn't|won't|wouldn't|couldn't|shouldn't|"
    r"can't|couldn't|let's|that's|there's|here's|what's|who's|"
    r"gonna|wanna|gotta)\b",
    re.IGNORECASE,
)

# Emoji pattern (basic Unicode emoji ranges)
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f1e0-\U0001f1ff"  # flags
    "\U00002702-\U000027b0"  # dingbats
    "\U0001f900-\U0001f9ff"  # supplemental symbols
    "]+",
)

# Sentence splitting regex
_SENTENCE_SPLIT = re.compile(r"[.!?]+\s+")


class BrandVoiceService:
    """Analyzes user content history to extract and learn brand voice patterns."""

    MIN_CONTENT_PIECES = 5

    async def analyze_and_learn(self, user_id: str) -> dict:
        """Full pipeline: fetch history -> analyze -> persist to brand profile.

        Args:
            user_id: The user whose content to analyze.

        Returns:
            Dict with success status, voice_profile if ready, or reason if not.
        """
        texts = await self.get_content_history(user_id)

        analysis = self.analyze_content_samples(texts)
        if not analysis["ready"]:
            return {
                "success": False,
                "reason": analysis["reason"],
                "content_count": len(texts),
            }

        voice_profile = analysis["voice_profile"]

        persist_result = await self.persist_voice_to_brand_profile(user_id, voice_profile)

        return {
            "success": True,
            "voice_profile": voice_profile,
            "persist_result": persist_result,
            "content_count": len(texts),
        }

    async def get_content_history(self, user_id: str, limit: int = 50) -> list[str]:
        """Fetch user's content texts from ContentService.

        Args:
            user_id: The user whose content to fetch.
            limit: Maximum number of content records to retrieve.

        Returns:
            List of content text strings.
        """
        from app.services.content_service import ContentService

        service = ContentService()
        records = await service.list_content(user_id=user_id, limit=limit)

        texts = []
        for record in records:
            content = record.get("content", "")
            if content and len(content.strip()) > 20:
                texts.append(content.strip())

        return texts

    def analyze_content_samples(self, texts: list[str]) -> dict:
        """Pure function: analyze text samples, return voice features.

        Requires at least MIN_CONTENT_PIECES texts. Returns a voice profile
        with tone, vocabulary, and sentence pattern features.

        Args:
            texts: List of content text strings to analyze.

        Returns:
            Dict with 'ready' bool, 'voice_profile' if ready, 'reason' if not.
        """
        if len(texts) < self.MIN_CONTENT_PIECES:
            return {
                "ready": False,
                "reason": f"Need at least {self.MIN_CONTENT_PIECES} content pieces (have {len(texts)})",
            }

        tone = self.extract_tone_markers(texts)
        vocab = self.extract_vocabulary_patterns(texts)
        sentences = self.extract_sentence_patterns(texts)

        voice_profile = self.build_voice_profile(tone, vocab, sentences)

        return {
            "ready": True,
            "voice_profile": voice_profile,
        }

    def extract_tone_markers(self, texts: list[str]) -> dict:
        """Extract tone markers from content samples.

        Identifies exclamation frequency, question frequency, emoji usage,
        and formality score.

        Args:
            texts: List of content text strings.

        Returns:
            Dict with exclamation_rate, question_rate, emoji_rate, formality_score.
        """
        total_sentences = 0
        exclamation_count = 0
        question_count = 0
        emoji_count = 0
        contraction_count = 0
        total_words = 0
        total_word_length = 0

        for text in texts:
            # Split into sentences
            sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
            if not sentences:
                sentences = [text]
            total_sentences += len(sentences)

            # Count exclamation and question marks
            exclamation_count += text.count("!")
            question_count += text.count("?")

            # Count emoji occurrences
            emoji_count += len(_EMOJI_PATTERN.findall(text))

            # Count contractions
            contraction_count += len(_CONTRACTIONS_PATTERN.findall(text))

            # Word-level analysis
            words = re.findall(r"\b[a-zA-Z]+\b", text)
            total_words += len(words)
            total_word_length += sum(len(w) for w in words)

        # Calculate rates (per sentence)
        if total_sentences == 0:
            total_sentences = 1  # avoid division by zero

        exclamation_rate = round(exclamation_count / total_sentences, 3)
        question_rate = round(question_count / total_sentences, 3)
        emoji_rate = round(emoji_count / total_sentences, 3)

        # Formality score: 0 (very casual) to 1 (very formal)
        # Factors: contractions (lower), emoji (lower), avg word length (higher),
        #          exclamation rate (lower)
        formality_signals: list[float] = []

        # Contraction density (more contractions = less formal)
        if total_words > 0:
            contraction_density = contraction_count / total_words
            # Scale: 0 contractions = 1.0, heavy contractions (0.05+) = 0.0
            formality_signals.append(max(0.0, 1.0 - contraction_density * 20))

        # Emoji density
        emoji_density = emoji_count / total_sentences
        formality_signals.append(max(0.0, 1.0 - emoji_density * 5))

        # Average word length (longer = more formal)
        if total_words > 0:
            avg_wl = total_word_length / total_words
            # Scale: 3 chars = 0.0, 7+ chars = 1.0
            formality_signals.append(min(1.0, max(0.0, (avg_wl - 3.0) / 4.0)))

        # Exclamation density (more = less formal)
        excl_density = exclamation_count / total_sentences
        formality_signals.append(max(0.0, 1.0 - excl_density * 2))

        formality_score = round(
            sum(formality_signals) / len(formality_signals) if formality_signals else 0.5,
            3,
        )

        return {
            "exclamation_rate": exclamation_rate,
            "question_rate": question_rate,
            "emoji_rate": emoji_rate,
            "formality_score": formality_score,
        }

    def extract_vocabulary_patterns(self, texts: list[str]) -> dict:
        """Extract vocabulary patterns: distinctive words, avg word length.

        Returns top-20 distinctive words (excluding stopwords) that appear
        across multiple content pieces.

        Args:
            texts: List of content text strings.

        Returns:
            Dict with distinctive_words (list) and avg_word_length (float).
        """
        # Track which texts each word appears in (document frequency)
        doc_freq: Counter = Counter()
        total_word_lengths: list[int] = []

        for text in texts:
            words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", text)]
            total_word_lengths.extend(len(w) for w in words)

            # Unique words per document for doc frequency
            unique_words = set(words)
            for word in unique_words:
                if word not in _STOPWORDS:
                    doc_freq[word] += 1

        # Distinctive words: appear in 2+ documents (characteristic of the author)
        min_docs = min(2, len(texts))  # at least 2 docs, or all if fewer
        distinctive = [
            word
            for word, count in doc_freq.most_common(50)
            if count >= min_docs
        ][:20]

        avg_word_length = round(
            sum(total_word_lengths) / len(total_word_lengths) if total_word_lengths else 0.0,
            2,
        )

        return {
            "distinctive_words": distinctive,
            "avg_word_length": avg_word_length,
        }

    def extract_sentence_patterns(self, texts: list[str]) -> dict:
        """Extract sentence-level patterns.

        Args:
            texts: List of content text strings.

        Returns:
            Dict with avg_sentence_length, sentence_length_variance, short_sentence_ratio.
        """
        all_lengths: list[int] = []

        for text in texts:
            sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
            if not sentences:
                sentences = [text]

            for sentence in sentences:
                word_count = len(re.findall(r"\b[a-zA-Z]+\b", sentence))
                if word_count > 0:
                    all_lengths.append(word_count)

        if not all_lengths:
            return {
                "avg_sentence_length": 0.0,
                "sentence_length_variance": 0.0,
                "short_sentence_ratio": 0.0,
            }

        avg = sum(all_lengths) / len(all_lengths)

        # Variance
        variance = sum((length - avg) ** 2 for length in all_lengths) / len(all_lengths)

        # Short sentence ratio (sentences with 6 or fewer words)
        short_count = sum(1 for length in all_lengths if length <= 6)
        short_ratio = short_count / len(all_lengths)

        return {
            "avg_sentence_length": round(avg, 2),
            "sentence_length_variance": round(variance, 2),
            "short_sentence_ratio": round(short_ratio, 3),
        }

    def build_voice_profile(self, tone: dict, vocab: dict, sentences: dict) -> dict:
        """Compile extracted features into a structured voice profile.

        Maps raw analysis into a profile with tone_summary, personality_traits,
        example_sentences placeholder, and formality_score.

        Args:
            tone: Output from extract_tone_markers.
            vocab: Output from extract_vocabulary_patterns.
            sentences: Output from extract_sentence_patterns.

        Returns:
            Dict with tone_summary, personality_traits, example_sentences,
            formality_score, avg_sentence_length, avg_word_count, common_phrases.
        """
        formality = tone.get("formality_score", 0.5)
        excl_rate = tone.get("exclamation_rate", 0)
        question_rate = tone.get("question_rate", 0)

        # Determine tone descriptors
        descriptors: list[str] = []

        # Formality axis
        if formality < 0.3:
            descriptors.append("casual")
        elif formality < 0.5:
            descriptors.append("conversational")
        elif formality < 0.7:
            descriptors.append("professional")
        else:
            descriptors.append("formal")

        # Energy axis
        if excl_rate > 0.3:
            descriptors.append("enthusiastic")
        elif excl_rate > 0.15:
            descriptors.append("energetic")

        # Engagement axis
        if question_rate > 0.2:
            descriptors.append("inquisitive")
        elif question_rate > 0.1:
            descriptors.append("engaging")

        # Sentence length axis
        avg_sent = sentences.get("avg_sentence_length", 10)
        if avg_sent < 8:
            descriptors.append("concise")
        elif avg_sent > 18:
            descriptors.append("detailed")

        # Short sentence style
        short_ratio = sentences.get("short_sentence_ratio", 0)
        if short_ratio > 0.3:
            descriptors.append("punchy")

        tone_summary = " and ".join(descriptors[:3]) if descriptors else "balanced"

        # Personality traits (more granular)
        traits: list[str] = list(descriptors)
        if vocab.get("avg_word_length", 0) > 5.5:
            traits.append("articulate")
        if formality < 0.4 and excl_rate > 0.1:
            traits.append("approachable")

        return {
            "tone_summary": tone_summary,
            "personality_traits": traits,
            "example_sentences": [],  # Populated by analyze_and_learn with real excerpts
            "formality_score": formality,
            "avg_sentence_length": sentences.get("avg_sentence_length", 0.0),
            "avg_word_count": vocab.get("avg_word_length", 0.0),
            "common_phrases": vocab.get("distinctive_words", [])[:10],
        }

    async def persist_voice_to_brand_profile(self, user_id: str, voice_profile: dict) -> dict:
        """Save learned voice to brand profile via update_brand_profile.

        Maps voice_profile fields to brand_profile fields:
        - tone_summary -> voice_tone
        - personality_traits -> voice_personality
        - example_sentences -> voice_examples (joined with ' | ')

        Args:
            user_id: The user whose brand profile to update.
            voice_profile: The compiled voice profile dict.

        Returns:
            Result dict from update_brand_profile.
        """
        examples = voice_profile.get("example_sentences", [])
        examples_str = " | ".join(examples) if examples else ""

        result = await update_brand_profile(
            voice_tone=voice_profile.get("tone_summary", ""),
            voice_personality=voice_profile.get("personality_traits", []),
            voice_examples=examples_str,
            user_id=user_id,
        )
        return result
