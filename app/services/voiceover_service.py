"""Voiceover generation service with graceful fallback.

Primary path uses Google Cloud Text-to-Speech when available/configured.
If unavailable, returns a structured failure without breaking video generation.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def synthesize_speech(
    text: str,
    *,
    language_code: str = "en-US",
    voice_name: str | None = None,
    speaking_rate: float = 1.0,
    pitch: float = 0.0,
) -> dict[str, Any]:
    """Synthesize speech to MP3 bytes.

    Returns:
        dict with:
        - success: bool
        - audio_bytes: bytes | None
        - mime_type: str | None
        - error: str | None
    """
    clean_text = (text or "").strip()
    if not clean_text:
        return {
            "success": False,
            "audio_bytes": None,
            "mime_type": None,
            "error": "Empty text",
        }

    try:
        from google.cloud import texttospeech
    except Exception as exc:  # pragma: no cover - depends on optional package
        logger.info("Google Cloud TTS unavailable: %s", exc)
        return {
            "success": False,
            "audio_bytes": None,
            "mime_type": None,
            "error": "google-cloud-texttospeech not installed",
        }

    try:
        client = texttospeech.TextToSpeechClient()
        input_text = texttospeech.SynthesisInput(text=clean_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name or os.getenv("DIRECTOR_TTS_VOICE", "en-US-Neural2-F"),
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
        )
        response = client.synthesize_speech(
            request={"input": input_text, "voice": voice, "audio_config": audio_config}
        )
        return {
            "success": True,
            "audio_bytes": response.audio_content,
            "mime_type": "audio/mpeg",
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - external dependency branch
        logger.warning("TTS synthesis failed: %s", exc)
        return {
            "success": False,
            "audio_bytes": None,
            "mime_type": None,
            "error": str(exc),
        }
